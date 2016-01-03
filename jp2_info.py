# jp2_info.py

# adapted from Loris img_info, stripped down just to interrogate a JP2 ONLY, not to model an info.json
# However - take a look at https://github.com/loris-imageserver/loris/blob/development/loris/img_info.py
# (Jon generates the info.json from the jp2 using this)

from collections import deque
from logging import getLogger
from math import ceil
from threading import Lock
import errno
import fnmatch
import os
import struct
from urllib import unquote
from sys import exit

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

logger = getLogger(__name__)


class Jp2Info(object):

    __slots__ = ('path', 'scaleFactors', 'width', 'tiles', 'height', 'sizes', 'color_profile_bytes', 'src_img_fp')

    @staticmethod
    def from_jp2_file(src_img_fp):

        new_inst = Jp2Info()
        new_inst.src_img_fp = src_img_fp
        new_inst.tiles = []
        new_inst.sizes = None
        new_inst.scaleFactors = None
        new_inst.path = src_img_fp
        new_inst._from_jp2(src_img_fp)

        return new_inst

 
    def _from_jp2(self, fp):
        '''Get info about a JP2.
        '''
        logger.debug('Extracting info from JP2 file.')
        
        scaleFactors = []

        jp2 = open(fp, 'rb')
        b = jp2.read(1)

        window = deque([], 4)

        while ''.join(window) != 'ihdr':
            b = jp2.read(1)
            c = struct.unpack('c', b)[0]
            window.append(c)
        self.height = int(struct.unpack(">I", jp2.read(4))[0]) # height (pg. 136)
        self.width = int(struct.unpack(">I", jp2.read(4))[0]) # width
        logger.debug("width: " + str(self.width))
        logger.debug("height: " + str(self.height))

        # Figure out color or grayscale.
        # Depending color profiles; there's probably a better way (or more than
        # one, anyway.)
        # see: JP2 I.5.3.3 Colour Specification box
        while ''.join(window) != 'colr':
            b = jp2.read(1)
            c = struct.unpack('c', b)[0]
            window.append(c)

        colr_meth = struct.unpack('B', jp2.read(1))[0]
        logger.debug('colr METH: %d' % (colr_meth,))

        # PREC and APPROX, 1 byte each
        colr_prec = struct.unpack('b', jp2.read(1))[0]
        colr_approx = struct.unpack('B', jp2.read(1))[0]
        logger.debug('colr PREC: %d' % (colr_prec))
        logger.debug('colr APPROX: %d' % (colr_approx))

        if colr_meth == 1: # Enumerated Colourspace
            self.color_profile_bytes = None
            enum_cs = int(struct.unpack(">HH", jp2.read(4))[1])
            logger.debug('Image contains an enumerated colourspace: %d' % (enum_cs,))
            logger.debug('Enumerated colourspace: %d' % (enum_cs))
            if enum_cs == 16: # sRGB
                #self.profile[1]['qualities'] += ['gray', 'color']
                pass
            elif enum_cs == 17: # grayscale
                #self.profile[1]['qualities'] += ['gray']
                pass
            elif enum_cs == 18: # sYCC
                pass
            else:
                msg =  'Enumerated colourspace is neither "16", "17", or "18". '
                msg += 'See jp2 spec pg. 139.'
                logger.warn(msg)
        elif colr_meth == 2:
            # (Restricted ICC profile).
            logger.debug('Image contains a restricted, embedded colour profile')
            # see http://www.color.org/icc-1_1998-09.pdf, page 18.
            self.assign_color_profile(jp2)
        else:
            logger.warn('colr METH is neither "1" or "2". See jp2 spec pg. 139.')

            # colr METH 3 = Any ICC method, colr METH 4 = Vendor Colour method
            # See jp2 spec pg. 182 -  Table M.24 (Color spec box legal values)
            if colr_meth <= 4 and -128 <= colr_prec <= 127 and 1 <= colr_approx <= 4:
                self.assign_color_profile(jp2)

        window =  deque(jp2.read(2), 2)
        while map(ord, window) != [0xFF, 0x4F]: # (SOC - required, see pg 14)
            window.append(jp2.read(1))
        while map(ord, window) != [0xFF, 0x51]:  # (SIZ  - required, see pg 14)
            window.append(jp2.read(1))
        jp2.read(20) # through Lsiz (16), Rsiz (16), Xsiz (32), Ysiz (32), XOsiz (32), YOsiz (32)
        tile_width = int(struct.unpack(">I", jp2.read(4))[0]) # XTsiz (32)
        tile_height = int(struct.unpack(">I", jp2.read(4))[0]) # YTsiz (32)
        logger.debug("tile width: " + str(tile_width))
        logger.debug("tile height: " + str(tile_height))
        self.tiles.append( { 'width' : tile_width } )
        if tile_width != tile_height:
            self.tiles[0]['height'] = tile_height
        jp2.read(10) # XTOsiz (32), YTOsiz (32), Csiz (16)

        window =  deque(jp2.read(2), 2)
        # while (ord(b) != 0xFF): b = jp2.read(1)
        # b = jp2.read(1) # 0x52: The COD marker segment
        while map(ord, window) != [0xFF, 0x52]:  # (COD - required, see pg 14)
            window.append(jp2.read(1))

        jp2.read(7) # through Lcod (16), Scod (8), SGcod (32)
        levels = int(struct.unpack(">B", jp2.read(1))[0])
        logger.debug("levels: " + str(levels))
        scaleFactors = [pow(2, l) for l in range(0,levels+1)]
        self.tiles[0]['scaleFactors'] = scaleFactors
        jp2.read(4) # through code block stuff

        # We may have precincts if Scod or Scoc = xxxx xxx0
        # But we don't need to examine as this is the last variable in the
        # COD segment. Instead check if the next byte == 0xFF. If it is,
        # we don't have a Precint size parameter and we've moved on to either
        # the COC (optional, marker = 0xFF53) or the QCD (required,
        # marker = 0xFF5C)
        b = jp2.read(1)
        if ord(b) != 0xFF:
            if self.tiles[0]['width'] == self.width \
                and self.tiles[0].get('height') in (self.height, None):
                # Clear what we got above in SIZ and prefer this. This could
                # technically break as it's possible to have precincts inside tiles.
                # Let's wait for that to come up....
                self.tiles = []

                for level in range(levels+1):
                    i = int(bin(struct.unpack(">B", b)[0])[2:].zfill(8),2)
                    x = i&15
                    y = i >> 4
                    w = 2**x
                    h = 2**y
                    b = jp2.read(1)
                    try:
                        entry = next((i for i in self.tiles if i['width'] == w))
                        entry['scaleFactors'].append(pow(2, level))
                    except StopIteration:
                        self.tiles.append({'width':w, 'scaleFactors':[pow(2, level)]})

        jp2.close()

        self.sizes = []
        [self.sizes.append( { 'width' : w, 'height' : h } )
            for w,h in self.sizes_for_scales(scaleFactors)]
        self.sizes.sort(key=lambda size: max([size['width'], size['height']]))

    def assign_color_profile(self, jp2):
        profile_size_bytes = jp2.read(4)
        profile_size = int(struct.unpack(">I", profile_size_bytes)[0])
        self.color_profile_bytes = profile_size_bytes + jp2.read(profile_size-4)

    def sizes_for_scales(self, scales):
        fn = Jp2Info.scale_dim
        return [(fn(self.width, sf), fn(self.height, sf)) for sf in scales]

    @staticmethod
    def scale_dim(dim_len, scale):
        return int(ceil(dim_len * 1.0/scale))
        
        

