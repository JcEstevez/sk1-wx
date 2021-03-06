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
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

from sk1 import _
from sk1.resources import icons

from generic import PrefPanel


class GridPrefs(PrefPanel):
    pid = 'Grid'
    name = _('Grid and guides')
    title = _('Grid and guides options')
    icon_id = icons.PD_PREFS_GRID

    def __init__(self, app, dlg, *args):
        PrefPanel.__init__(self, app, dlg)
