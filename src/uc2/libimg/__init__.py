# -*- coding: utf-8 -*-
#
#  Copyright (C) 2015 by Igor E. Novikov
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import os
import cairo
from copy import deepcopy
from base64 import b64encode
from cStringIO import StringIO
from PIL import Image, ImageOps

from uc2.cms import val_255
from uc2.libimg import magickwand
from uc2.uc2const import IMAGE_CMYK, IMAGE_RGB, IMAGE_RGBA, IMAGE_LAB
from uc2.uc2const import IMAGE_GRAY, IMAGE_MONO, DUOTONES, SUPPORTED_CS
from uc2 import uc2const
from uc2.utils import fsutils

LOG = logging.getLogger(__name__)


def get_version():
    return Image.PILLOW_VERSION


def get_magickwand_version():
    return magickwand.get_magickwand_version()


def check_image(path):
    try:
        Image.open(path)
        LOG.debug('PIL check: True')
        return True
    except Exception:
        return magickwand.check_image_file(path)


def _get_saver_fmt(img):
    if img.mode == IMAGE_CMYK:
        return 'TIFF'
    return 'PNG'


def invert_image(cms, bmpstr):
    image_stream = StringIO()
    raw_image = Image.open(StringIO(bmpstr))
    raw_image.load()

    if raw_image.mode == IMAGE_MONO:
        raw_image = ImageOps.invert(raw_image.convert(IMAGE_GRAY))
        raw_image = raw_image.convert(IMAGE_MONO)
    elif raw_image.mode == IMAGE_CMYK:
        raw_image = cms.convert_image(raw_image, IMAGE_RGB)
        inv_image = ImageOps.invert(raw_image)
        raw_image = cms.convert_image(inv_image, IMAGE_CMYK)
    elif raw_image.mode == IMAGE_LAB:
        raw_image = cms.convert_image(raw_image, IMAGE_RGB)
        inv_image = ImageOps.invert(raw_image)
        raw_image = cms.convert_image(inv_image, IMAGE_LAB)
    else:
        raw_image = ImageOps.invert(raw_image)

    raw_image.save(image_stream, format=_get_saver_fmt(raw_image))
    return image_stream.getvalue()


def convert_image(cms, pixmap, colorspace, raw=False):
    image_stream = StringIO()
    if pixmap.colorspace in DUOTONES and colorspace not in DUOTONES:
        cdata_stream = StringIO()
        pixmap.cache_cdata.write_to_png(cdata_stream)
        cdata_stream.seek(0)
        raw_image = Image.open(cdata_stream)
        raw_image.load()
        raw_image = raw_image.convert("RGB")
    else:
        raw_image = Image.open(StringIO(pixmap.bitmap))
        raw_image.load()
    raw_image = cms.convert_image(raw_image, colorspace)
    if raw:
        return raw_image
    raw_image.save(image_stream, format=_get_saver_fmt(raw_image))
    return image_stream.getvalue()


def convert_duotone_to_image(cms, pixmap, cs=None):
    update_image(cms, pixmap)
    fg = pixmap.style[3][0]
    bg = pixmap.style[3][1]
    raw_image = Image.open(StringIO(pixmap.bitmap))
    raw_image.load()
    fg_img = bg_img = None
    fg_cs = bg_cs = uc2const.IMAGE_RGB
    if pixmap.colorspace == uc2const.IMAGE_MONO:
        raw_image = raw_image.convert(IMAGE_GRAY)
    size = raw_image.size
    if cs == uc2const.IMAGE_CMYK:
        if fg:
            fg = tuple(cms.get_cmyk_color255(fg))
        if bg:
            bg = tuple(cms.get_cmyk_color255(bg))
        fg_cs = bg_cs = cs
    elif cs == uc2const.IMAGE_RGB:
        if fg:
            fg = tuple(cms.get_rgb_color255(fg))
        if bg:
            bg = tuple(cms.get_rgb_color255(bg))
        fg_cs = bg_cs = cs
    else:
        if fg:
            fg_cs = fg[0]
            fg = tuple(val_255(cms.get_color(fg, fg_cs)[1]))
        if bg:
            bg_cs = bg[0]
            bg = tuple(val_255(cms.get_color(bg, bg_cs)[1]))
    if fg:
        fg_img = Image.new(fg_cs, size, fg)
    if bg:
        bg_img = Image.new(bg_cs, size, bg)

    fg_alpha = ImageOps.invert(raw_image)
    bg_alpha = raw_image
    if pixmap.has_alpha():
        alpha_chnl = Image.open(StringIO(pixmap.get_alpha_channel()))
        alpha_chnl.load()
        alpha_chnl = ImageOps.invert(alpha_chnl)
        comp_img = Image.new('L', size, 0)
        fg_alpha.paste(comp_img, (0, 0), alpha_chnl)
        bg_alpha.paste(comp_img, (0, 0), alpha_chnl)
    return (fg_img, fg_alpha), (bg_img, bg_alpha)


def extract_bitmap(pixmap, filepath):
    ext = '.png'
    if pixmap.colorspace == IMAGE_CMYK:
        ext = '.tiff'
    if not os.path.splitext(filepath)[1] == ext:
        filepath = os.path.splitext(filepath)[0] + ext
    fileptr = fsutils.get_fileptr(filepath, True)
    fileptr.write(pixmap.bitmap)
    fileptr.close()
    if pixmap.has_alpha():
        filepath = os.path.splitext(filepath)[0] + '_alphachannel.png'
        fileptr = fsutils.get_fileptr(filepath, True)
        fileptr.write(pixmap.get_alpha_channel())
        fileptr.close()


def update_image(cms, pixmap, force_proofing=False):
    png_stream = StringIO()

    raw_image = Image.open(StringIO(pixmap.bitmap))
    raw_image.load()

    if pixmap.colorspace in DUOTONES:
        if pixmap.colorspace == IMAGE_MONO:
            raw_image = raw_image.convert(IMAGE_GRAY)
        fg = pixmap.style[3][0]
        bg = pixmap.style[3][1]
        fg_color = (0, 0, 0, 0)
        bg_color = (255, 255, 255, 0)
        if fg:
            fg_color = tuple(cms.get_display_color255(fg)) + (
                int(fg[2] * 255.0),)
        if bg:
            bg_color = tuple(cms.get_display_color255(bg)) + (
                int(bg[2] * 255.0),)
        cache_image = Image.new(IMAGE_RGBA, pixmap.size, fg_color)
        bg_image = Image.new(IMAGE_RGBA, pixmap.size, bg_color)
        cache_image.paste(bg_image, (0, 0), raw_image)
        if force_proofing:
            rgb_image = cache_image.convert(IMAGE_RGB)
            rgb_image = cms.convert_image(rgb_image, IMAGE_CMYK)
            rgb_image = cms.get_display_image(rgb_image)
            rgb_image.putalpha(cache_image.split()[3])
            cache_image = rgb_image
    else:
        if force_proofing and not raw_image.mode == IMAGE_CMYK:
            raw_image = cms.convert_image(raw_image, IMAGE_CMYK)
        cache_image = cms.get_display_image(raw_image)

    if pixmap.has_alpha():
        raw_alpha = pixmap.get_alpha_channel()
        raw_alpha = Image.open(StringIO(raw_alpha))
        if cache_image.mode == IMAGE_RGB:
            cache_image = cache_image.convert(IMAGE_RGBA)
        elif cache_image.mode == IMAGE_RGBA:
            cache_alpha = Image.new(IMAGE_GRAY, pixmap.size)
            mask = ImageOps.invert(cache_image.split()[3])
            raw_alpha.paste(cache_alpha, (0, 0), mask)
        cache_image.putalpha(raw_alpha)

    if cache_image:
        cache_image.save(png_stream, format='PNG')

    png_stream.seek(0)
    pixmap.cache_cdata = cairo.ImageSurface.create_from_png(png_stream)


def update_gray_image(cms, pixmap):
    png_stream = StringIO()

    raw_image = Image.open(StringIO(pixmap.bitmap))
    raw_image.load()

    if pixmap.colorspace in DUOTONES:
        if pixmap.colorspace == IMAGE_MONO:
            raw_image = raw_image.convert(IMAGE_GRAY)
        fg = pixmap.style[3][0]
        bg = pixmap.style[3][1]
        fg_color = (0, 0, 0, 0)
        bg_color = (255, 255, 255, 0)
        if fg:
            fg_color = tuple(cms.get_display_color255(fg)) + (
                int(fg[2] * 255.0),)
        if bg:
            bg_color = tuple(cms.get_display_color255(bg)) + (
                int(bg[2] * 255.0),)
        cache_image = Image.new(IMAGE_RGBA, pixmap.size, fg_color)
        bg_image = Image.new(IMAGE_RGBA, pixmap.size, bg_color)
        cache_image.paste(bg_image, (0, 0), raw_image)
        rgb_image = cache_image.convert(IMAGE_GRAY).convert(IMAGE_RGBA)
        if pixmap.has_alpha():
            raw_alpha = pixmap.get_alpha_channel()
            raw_alpha = Image.open(StringIO(raw_alpha))
            cache_alpha = Image.new(IMAGE_GRAY, pixmap.size)
            mask = ImageOps.invert(cache_image.split()[3])
            raw_alpha.paste(cache_alpha, (0, 0), mask)
            rgb_image.putalpha(raw_alpha)
        else:
            rgb_image.putalpha(cache_image.split()[3])
    else:
        raw_image = raw_image.convert(IMAGE_GRAY)
        if pixmap.has_alpha():
            raw_alpha = pixmap.get_alpha_channel()
            raw_alpha = Image.open(StringIO(raw_alpha))
            rgb_image = raw_image.convert(IMAGE_RGBA)
            rgb_image.putalpha(raw_alpha)
        else:
            rgb_image = raw_image.convert(IMAGE_RGB)

    rgb_image.save(png_stream, format='PNG')

    png_stream.seek(0)
    pixmap.cache_gray_cdata = cairo.ImageSurface.create_from_png(png_stream)


def extract_profile(raw_content):
    profile = None
    mode = None
    try:
        img = Image.open(StringIO(raw_content))
        if 'icc_profile' in img.info:
            profile = img.info.get('icc_profile')
            mode = img.mode
    except Exception:
        pass
    return profile, mode


def set_image_data(cms, pixmap, raw_content):
    alpha = ''
    profile, mode = extract_profile(raw_content)

    base_stream, alpha_stream = magickwand.process_image(raw_content)
    base_image = Image.open(base_stream)
    base_image.load()

    pixmap.size = () + base_image.size
    if base_image.mode not in SUPPORTED_CS:
        base_image = base_image.convert(IMAGE_RGB)

    if base_image.mode not in SUPPORTED_CS[1:]:
        profile = mode = None

    if profile and base_image.mode == mode:
        try:
            base_image = cms.adjust_image(base_image, profile)
        except Exception:
            pass

    pixmap.colorspace = base_image.mode

    fobj = StringIO()
    base_image = base_image.copy()
    base_image.save(fobj, format=_get_saver_fmt(base_image))
    bmp = fobj.getvalue()

    style = deepcopy(pixmap.config.default_image_style)
    if base_image.mode in [IMAGE_RGB, IMAGE_LAB]:
        style[3] = deepcopy(pixmap.config.default_rgb_image_style)

    if alpha_stream:
        alpha_image = Image.open(alpha_stream)
        alpha_image.load()
        if alpha_image.mode == 'P':
            alpha_image = alpha_image.convert(IMAGE_RGBA)
        if alpha_image.mode in ['LA', IMAGE_RGBA]:
            if alpha_image.mode == 'LA':
                band = alpha_image.split()[1]
            else:
                band = alpha_image.split()[3]
            fobj = StringIO()
            band.save(fobj, format=_get_saver_fmt(band))
            alpha = fobj.getvalue()

    pixmap.bitmap = bmp
    pixmap.set_alpha_channel(alpha)
    pixmap.style = style


def transpose(image_obj, method=Image.FLIP_TOP_BOTTOM):
    image = Image.open(StringIO(image_obj.bitmap))
    image.load()

    image = image.transpose(method)
    fobj = StringIO()
    image.save(fobj, format='TIFF')
    image_obj.bitmap = fobj.getvalue()
    if image_obj.has_alpha():
        alpha = Image.open(StringIO(image_obj.get_alpha_channel()))
        alpha.load()

        alpha = alpha.transpose(method)
        fobj = StringIO()
        alpha.save(fobj, format=_get_saver_fmt(alpha))
        image_obj.set_alpha_channel(fobj.getvalue())
    image_obj.cache_cdata = None


def flip_top_to_bottom(image_obj):
    transpose(image_obj)


def flip_left_to_right(image_obj):
    transpose(image_obj, Image.FLIP_LEFT_RIGHT)


EPS_HEADER = '%!PS-Adobe-3.0 EPSF-3.0'


def read_pattern(raw_content):
    if raw_content[:len(EPS_HEADER)] == EPS_HEADER:
        return b64encode(raw_content), 'EPS'
    fobj, flag = magickwand.process_pattern(raw_content)
    return b64encode(fobj.getvalue()), flag
