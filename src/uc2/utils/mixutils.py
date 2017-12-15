# -*- coding: utf-8 -*-
#
#  Copyright (C) 2016 by Igor E. Novikov
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


def merge_cnf(cnf=None, kw=None):
    cnf = cnf or {}
    if kw:
        cnf.update(kw)
    return cnf


LOGGING_MAP = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARN': logging.WARN,
    'WARNING': logging.WARN,
    'ERROR': logging.ERROR,
}


def config_logging(filepath, level='INFO'):
    level = LOGGING_MAP.get(level.upper(), logging.INFO)
    logging.basicConfig(level=level,
                        filename=filepath,
                        filemode='w')
