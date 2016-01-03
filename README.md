# jp2iser

Experiment with jp2 and thumbnail creation, using key bits of Loris.

Given a source image, create a tile-optimised JP2 and thumbnail jpgs at specified sizes

### Timings

For a 100MB source bitmap (38 Megapixel) this will produce the JP2 and derivatives in about 0.5s

If the source image is already a JP2 then the derivatives alone can be created very quickly (like tile generation in Loris)

e.g., on my i5 running PIL part single threaded:

3 thumbs confined to 400, 200 and 100 pixel squares takes 44ms

4 thumbs confined to 1000, 400, 200 and 100 pixel squares takes 290ms

If the source image is already a tiff, bmp or other file that Kakadu can accept directly then the process is quicker

If the source image is a JPG or other bitmap that Kakadu can't use directly, we convert to bitmap first.


NOT PRODUCTION!

The JP2 header parsing code and transform using expand are pretty much taken from Loris, and it has the same dependencies regarding image libs:

### Dependencies

```
$ sudo apt-get install libjpeg-turbo8-dev libfreetype6-dev zlib1g-dev liblcms2-dev liblcms-utils libtiff5-dev python-dev libwebp-dev 
$ sudo pip install Pillow
```
The various working dirs are wired into settings.py

### Usage

```
$ python jp2iser.py /path/to/src_image [s1 s2 s3...]
```

```src_image``` can be anything that PIL can turn into a bitmap.

e.g.,

```
$ python jp2iser.py /path/to/my_image.tiff 400 200 100
```

### TODO

* implement rasterise_pdf using GhostScript
* Logic for determining whether, if already a JP2, we accept as-is or further optimise
* Put the colour profile stuff back in
* etc
