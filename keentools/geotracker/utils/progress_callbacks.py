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

from ...utils.kt_logging import KTLogger
from ...addon_config import gt_settings
from ...utils.bpy_common import bpy_progress_update
from ...blender_independent_packages.pykeentools_loader import module as pkt_module


_log = KTLogger(__name__)


class TRProgressCallBack(pkt_module().TrackerProgressCallback):
    def __init__(self, start=-1, end=-1):
        super().__init__()
        self.last_progress = -1
        self.start = start
        self.end = end
        self.counter = 0

    def set_progress_and_check_abort(self, progress):
        _log.output(f'set_progress_and_check_abort: {progress}')
        bpy_progress_update(progress)
        self.last_progress = progress
        self.counter += 1
        assert not self.start <= progress <= self.end
        return False

    def set_total_frames(self, arg0):
        _log.output(f'set_total_frames: {arg0}')


class RFProgressCallBack(pkt_module().RefineProgressCallback):
    def __init__(self):
        super().__init__()
        self.refined_frames = 0
        self.total_frames = 100

    def set_progress_and_check_abort(self, progress):
        bpy_progress_update(progress)
        self.refined_frames += 1
        _log.output('Refine set_progress_and_check_abort: {}'.format(progress))
        _log.output(_log.color(
            'magenta',
            f'refined_frames: {self.refined_frames}/{self.total_frames}'))
        if type(self.total_frames) == int and self.total_frames > 0:
            settings = gt_settings()
            settings.user_percent = 100 * self.refined_frames / self.total_frames
            _log.output(f'REFINE PERCENT: {settings.user_percent}')
        return False

    def set_progress_stage(self, arg0):
        _log.output('Refine set_progress_stage: {}'.format(arg0))
        self.total_frames = arg0
        self.refined_frames = 0

    def set_total_stages(self, arg0):
        _log.output('Refine set_total_stages: {}'.format(arg0))
