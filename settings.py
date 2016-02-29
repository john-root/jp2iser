
KDU_COMPRESS = '/usr/local/bin/kakadu/kdu_compress'
KDU_EXPAND = '/usr/local/bin/kakadu/kdu_expand'


OUTPUT_DIR = '/home/giskard/dev/jp2iser/out/'
TMP_DIR = '/home/ubuntu/jp2iser/tmp/'

KDU_LIB = '/usr/local/bin/kakadu'
MKFIFO = '/usr/bin/mkfifo'

# note the double escape of braces for formatting
CMD_COMPRESS = ('{kdu} -i {input} -o {output} Clevels=7 "Cblk={{64,64}}" "Cuse_sop=yes" '
                '"ORGgen_plt=yes" "ORGtparts=R" "Corder=RPCL" -rate 0.5 '
                '"Cprecincts={{256,256}},{{256,256}},{{256,256}},{{128,128}},{{128,128}},{{64,64}},{{64,64}},{{32,32}},{{16,16}}"')

map_profile_to_srgb = True
srgb_profile_fp = '/usr/share/color/icc/colord/sRGB.icc'
