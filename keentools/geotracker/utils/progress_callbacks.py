# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2022 KeenTools

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# ##### END GPL LICENSE BLOCK #####

import logging
import bpy

from ...blender_independent_packages.pykeentools_loader import module as pkt_module


class TRProgressCallBack(pkt_module().TrackerProgressCallback):
    def __init__(self, start=-1, end=-1):
        super().__init__()
        self.last_progress = -1
        self.start = start
        self.end = end
        self.counter = 0

    def set_progress_and_check_abort(self, progress):
        logger = logging.getLogger(__name__)
        log_output = logger.info
        log_output(f'set_progress_and_check_abort: {progress}')
        bpy.context.window_manager.progress_update(progress)
        self.last_progress = progress
        self.counter += 1
        assert not self.start <= progress <= self.end
        return True

    def set_total_frames(self, arg0):
        logger = logging.getLogger(__name__)
        log_output = logger.info
        log_output(f'set_total_frames: {arg0}')
