KDU_COMPRESS = '/opt/tizer/kakadu/current/kdu_compress'
KDU_EXPAND = '/opt/tizer/kakadu/current/kdu_expand'

OUTPUT_DIR = '/opt/tizer/out/'
TMP_DIR = '/opt/tizer/tmp/'

KDU_LIB = '/opt/tizer/kakadu/current/'
MKFIFO = '/usr/bin/mkfifo'


IMAGE_MODES = {
    "L": "-no_palette",        # greyscale
    "1": "-no_palette",        # bitonal
    "RGB": "-jp2_space sRGB"  # RGB
}

# note the double escape of braces for formatting
CMD_COMPRESS = {
    "kdu_low":  '{kdu} -i {input} -o {output} Clevels=7 "Cblk={{64,64}}" "Cuse_sop=yes" {image_mode}  ' +
            '"ORGgen_plt=yes" "ORGtparts=R" "Corder=RPCL" -rate 0.5 ' +
            '"Cprecincts={{256,256}},{{256,256}},{{256,256}},{{128,128}},' +
            '{{128,128}},{{64,64}},{{64,64}},{{32,32}},{{16,16}}"',
    "kdu_med":  '{kdu} -i {input} -o {output} Clevels=7 "Cblk={{64,64}}" "Cuse_sop=yes" {image_mode}  ' +
            '"ORGgen_plt=yes" "ORGtparts=R" "Corder=RPCL" -rate 2 ' +
            '"Cprecincts={{256,256}},{{256,256}},{{256,256}},{{128,128}},' +
            '{{128,128}},{{64,64}},{{64,64}},{{32,32}},{{16,16}}"',
    "kdu_high": '{kdu} -i {input} -o {output} Clevels=7 "Cblk={{64,64}}" "Cuse_sop=yes" {image_mode}  ' +
            '"ORGgen_plt=yes" "ORGtparts=R" "Corder=RPCL" -rate 4 ' +
            '"Cprecincts={{256,256}},{{256,256}},{{256,256}},{{128,128}},' +
            '{{128,128}},{{64,64}},{{64,64}},{{32,32}},{{16,16}}"',
    "kdu_max":  '{kdu} -i {input} -o {output} Clevels=7 "Cblk={{64,64}}" "Cuse_sop=yes" {image_mode}  ' +
            '"ORGgen_plt=yes" "ORGtparts=R" "Corder=RPCL" -rate - ' +
            '"Cprecincts={{256,256}},{{256,256}},{{256,256}},{{128,128}},' +
            '{{128,128}},{{64,64}},{{64,64}},{{32,32}},{{16,16}}"',

}

map_profile_to_srgb = True
srgb_profile_fp = '/opt/tizer/icc/sRGB.icc'
