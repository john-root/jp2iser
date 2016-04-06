import time
import os
import shutil
import base64
from math import ceil, log
import random
from settings import *
from PIL import Image
from PIL.ImageFile import Parser
from PIL.ImageCms import profileToProfile
import cStringIO
import string
import subprocess
from jp2_info import Jp2Info
import uuid
import pystache
import json


def path_parts(filepath):
    head, filename = os.path.split(filepath)
    namepart, extension = os.path.splitext(filename)
    return head, filename, namepart, extension.lower()[1:]


def process(filepath, destination=None, bounded_sizes=list(), bounded_folder=None, optimisation="kdu_med", jpeg_info_id="ID"):
    # Convert image file into tile-optimised JP2 and optionally additional derivatives
    start = time.clock()
    result = {}

    head, filename, namepart, extension = path_parts(filepath)
    print '%s  -- [%s] - %s.%s' % (head, filename, namepart, extension)

    print 'destination: %s' % destination
    jp2path = destination or os.path.join(OUTPUT_DIR, namepart + '.jp2')
    print 'Converting: ', filename
    print 'We want to make a JP2 at: ', jp2path

    if optimisation not in CMD_COMPRESS:
        optimisation = "kdu_med"

    if is_tile_optimised_jp2(filepath, extension):
        print filename, 'is already optimised for tiles, proceeding to next stage'
        shutil.copyfile(filepath, jp2path)
    else:
        kdu_ready, image_mode = get_kdu_ready_file(filepath, extension)
        make_jp2_from_image(kdu_ready, jp2path, optimisation, image_mode)
        result["jp2"] = jp2path
        if filepath != kdu_ready:
            # TODO - do this properly
            print 'removing', kdu_ready, 'as it was a temporary file'
            os.remove(kdu_ready)

    jp2_data = Jp2Info.from_jp2_file(jp2path)
    jp2_info_template = open('jp2info.mustache').read()

    jp2_info = pystache.render(jp2_info_template, {
        "id": jpeg_info_id,
        "height": jp2_data.height,
        "width": jp2_data.width,
        "scale_factors": ",".join(map(str, get_scale_factors(jp2_data.width, jp2_data.height)))
    })

    if len(bounded_sizes) > 0:
        make_derivatives(jp2_data, result, jp2path, bounded_sizes, bounded_folder)

    elapsed = time.clock() - start
    print 'operation time', elapsed
    result["clockTime"] = int(elapsed * 1000)
    result["optimisation"] = optimisation
    result["jp2Info"] = base64.b64encode(jp2_info.encode('utf-8'))
    result["width"] = jp2_data.width
    result["height"] = jp2_data.height
    return result


def is_tile_optimised_jp2(filepath, extension):
    # test the file - is it a JP2? If so, does it need optimising?
    # TODO: for now always assume that JP2 files are good to go
    return extension == 'jp2'


def get_kdu_ready_file(filepath, extension):
    # From kdu_compress -usage:
    # 'Currently accepted image file formats are: TIFF (including BigTIFF),
    #  RAW (big-endian), RAWL (little-endian), BMP, PBM, PGM and PPM, as
    #  determined by the file suffix.'
    kdu_ready_formats = ['tif', 'bmp', 'raw', 'pbm', 'pgm', 'ppm']

    # during this processing we might be able to determine the mode. If not, leave as
    # none and we will do it later if reqired
    image_mode = None

    # we need to create a tiff for initial passing to kdu

    if extension[:3] in kdu_ready_formats:
        print filepath, 'can be converted directly'
    elif extension == 'pdf':
        filepath = rasterise_pdf(filepath)
    elif extension == 'jp2':
        print filepath, 'is not tile ready so needs to be reprocessed'
        filepath = get_tiff_from_kdu(filepath)
    else:
        filepath, image_mode = get_tiff_from_pillow(filepath)

    return filepath, image_mode


def get_output_file_path(filepath, new_extension):
    # use tmp directory, not like this!
    head, filename, namepart, extension = path_parts(filepath)
    myid = str(uuid.uuid4())
    return os.path.join(TMP_DIR, myid + '.' + namepart + '.' + new_extension)


def mock_file(filepath, new_extension):
    print 'creating mock file with extension', new_extension
    new_file_path = get_output_file_path(filepath, new_extension)
    shutil.copyfile(filepath, new_file_path)
    return new_file_path


def get_tiff_from_pillow(filepath):
    print 'making tiff using pillow from', filepath
    new_file_path = get_output_file_path(filepath, 'tiff')
    im = Image.open(filepath)
    if 'icc_profile' in im.info:
        print "converting profile"
        src_profile = cStringIO.StringIO(im.info['icc_profile'])
        im = profileToProfile(im, src_profile, srgb_profile_fp)
    im.save(new_file_path)  # , compression=None)

    image_mode = im.mode
    return new_file_path, image_mode


def get_tiff_from_kdu(filepath):
    print 'making tiff using kdu from', filepath
    # env = {
    #    'LD_LIBRARY_PATH': KDU_LIB,
    #    'PATH': KDU_EXPAND
    # }
    return mock_file(filepath, 'tiff')


def make_jp2_from_image(kdu_ready_image, jp2path, optimisation, image_mode=None):
    print 'making jp2 using kdu from', kdu_ready_image
    compress_env = {
        'LD_LIBRARY_PATH': KDU_LIB,
        'PATH': KDU_COMPRESS
    }
    compress_cmd = CMD_COMPRESS[optimisation]

    if image_mode is None:
        im = Image.open(kdu_ready_image)
        image_mode = im.mode

    # srgb or no_palette
    image_mode_replacement = IMAGE_MODES[image_mode]

    cmd = compress_cmd.format(kdu=KDU_COMPRESS, input=kdu_ready_image, output=jp2path,
                              image_mode=image_mode_replacement)
    print cmd
    res = subprocess.check_call(cmd, shell=True, env=compress_env)
    print 'subprocess returned', res


def make_derivatives(jp2, result, jp2path, bound_sizes, bound_folder):
    # bound_sizes should be a list of ints (square confinement)
    # make the first one from kdu_expand, then use Pillow to resize further
    # Note that Pillow's im.thumbnail function is really fast but doesn't
    # make very good quality thumbs; the PIL.Image.ANTIALIAS option
    # gives better results.

    # This could also be multi-threaded - BUT better for this process (jp2iser)
    # to be running on multiple threads and control it that way
    # i.e., a machine is processing this off the queue in parallel.
    print 'making derivatives'
    head, filename, namepart, extension = path_parts(jp2path)
    if bound_folder:
        prefix = bound_folder + namepart
    else:
        prefix = os.path.join(head, namepart)
    im = None
    for size in sorted(bound_sizes, reverse=True):
        if im is None:
            im = get_reduced_image_from_kdu(jp2, size)
        else:
            req_w, req_h = confine(jp2.width, jp2.height, size, size)
            im = im.resize((req_w, req_h), resample=Image.ANTIALIAS)

        jpg = prefix + '_' + str(size) + '.jpg'
        print 'saving', jpg
        im.save(jpg, quality=90)

        if "thumbs" not in result:
            result["thumbs"] = []
        result["thumbs"].append({
            "path": jpg,
            "width": im.width,
            "height": im.height
        })


def get_reduced_image_from_kdu(jp2, size):
    # This is basically like an IIIF op /full/!size,size/0/default.jpg
    # uses kdu via fifo as per Loris
    # returns PIL image object
    print 'making new pillow image for derivs at size', size
    im = None
    # extract the smallest possible resolution as the starting point for our transform ops
    req_w, req_h = confine(jp2.width, jp2.height, size, size)

    # mostly taken from transforms.py in Loris, but we want to return a Pillow image
    # color profile stuff has been removed for now

    n = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    fifo_fp = os.path.join(TMP_DIR, n + '.bmp')

    # kdu command
    q = ''  # '-quiet'
    t = '-num_threads 4'
    i = '-i "%s"' % (jp2.path,)
    o = '-o %s' % (fifo_fp,)
    reduce_arg = scales_to_reduce_arg(jp2, size)
    red = '-reduce %s' % (reduce_arg,) if reduce_arg else ''

    # kdu_expand -usage:
    # -reduce <discard levels>
    #    Set the number of highest resolution levels to be discarded.  The image
    #    resolution is effectively divided by 2 to the power of the number of
    #    discarded levels.

    kdu_cmd = ' '.join((KDU_EXPAND, q, i, t, red, o))

    # make the named pipe
    mkfifo_call = '%s %s' % (MKFIFO, fifo_fp)
    print 'Calling %s' % (mkfifo_call,)
    resp = subprocess.check_call(mkfifo_call, shell=True)

    expand_env = {
        'LD_LIBRARY_PATH': KDU_LIB,
        'PATH': KDU_EXPAND
    }

    try:
        # Start the kdu shellout. Blocks until the pipe is empty
        print 'Calling: %s' % (kdu_cmd,)
        print '########### kdu ###############'
        kdu_expand_proc = subprocess.Popen(kdu_cmd, shell=True, bufsize=-1,
                                           stderr=subprocess.PIPE, env=expand_env)

        f = open(fifo_fp, 'rb')
        print 'Opened %s' % fifo_fp

        # read from the named pipe into PIL
        p = Parser()
        while True:
            s = f.read(1024)
            if not s:
                break
            p.feed(s)
        im = p.close()  # a PIL.Image

        # finish kdu
        kdu_exit = kdu_expand_proc.wait()
        if kdu_exit != 0:
            print 'KDU ERROR'
            for e in kdu_expand_proc.stderr:
                print e

        if im.mode != "RGB":
            im = im.convert("RGB")

        imw, imh = im.size
        print 'we now have a PIL image %s x %s' % (imw, imh)
        if imw != req_w or imh != req_h:
            im = im.resize((req_w, req_h), resample=Image.ANTIALIAS)

    except:
        raise
    finally:
        kdu_exit = kdu_expand_proc.wait()
        if kdu_exit != 0:
            # TODO : add logging!
            # map(logger.error, map(string.strip, kdu_expand_proc.stderr))
            pass
        os.unlink(fifo_fp)

    return im


def get_scale_factors(width, height):

    tile_size = 256
    dimension = max(width, height)
    factors = [1]

    while dimension > tile_size:
        dimension //= 2
        factors.append(factors[-1] * 2)
    return factors


def scales_to_reduce_arg(jp2, size):
    # Scales from from JP2 levels, so even though these are from the tiles
    # info.json, it's easier than using the sizes from info.json
    scales = [s for t in jp2.tiles for s in t['scaleFactors']]
    arg = None
    if scales:
        req_w, req_h = confine(jp2.width, jp2.height, size, size)
        print 'confined to %s, %s' % (req_w, req_h)
        closest_scale = get_closest_scale(req_w, req_h, jp2.width, jp2.height, scales)
        reduce_arg = int(log(closest_scale, 2))
        arg = str(reduce_arg)
    return arg


def confine(w, h, req_w, req_h):
    # reduce longest edge to size
    if w <= req_w and h <= req_h:
        return w, h

    scale = min(req_w / (1.0 * w), req_h / (1.0 * h))
    return tuple(map(lambda d: int(round(d * scale)), [w, h]))


def get_closest_scale(req_w, req_h, full_w, full_h, scales):
    if req_w > full_w or req_h > full_h:
        return 1
    else:
        return max([s for s in scales if scale_dim(full_w, s) >= req_w and scale_dim(full_h, s) >= req_h])


def scale_dim(dim, scale):
    return int(ceil(dim / float(scale)))


def rasterise_pdf(pdf_file):
    print('not yet implemented. Will use Ghostscript and Pillow to create a tiff.')
    raise ValueError('no PDFs just yet')


if __name__ == "__main__":
    print('------------------------')
    import sys

    process(sys.argv[1], map(int, sys.argv[2:]))
