# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019  KeenTools

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

from bpy.types import Operator

from ..utils.kt_logging import KTLogger
from ..addon_config import Config, fb_settings, get_operator, ErrorType
from ..facebuilder_config import FBConfig
from ..utils import attrs
from ..utils.ui_redraw import show_ui_panel
from ..blender_independent_packages.pykeentools_loader import module as pkt_module
from ..utils.manipulate import center_viewports_on_object
from .ui_strings import buttons
from ..utils.bpy_common import bpy_create_object


_log = KTLogger(__name__)


class MESH_OT_FBAddHead(Operator):
    bl_idname = FBConfig.fb_add_head_operator_idname
    bl_label = buttons[bl_idname].label
    bl_description = buttons[bl_idname].description
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        _log.green(f'{self.__class__.__name__} execute')
        settings = fb_settings()
        loader = settings.loader()
        heads_deleted, cams_deleted = settings.fix_heads()
        try:
            obj = self.new_head()
            obj.location = settings.get_next_head_position()
        except ModuleNotFoundError as err:
            _log.error(f'ADD_HEAD_ERROR: ModuleNotFoundError\n{str(err)}')
            warn = get_operator(Config.kt_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.PktProblem)
            return {'CANCELLED'}
        except pkt_module().ModelLoadingException as err:
            _log.error(f'ADD_HEAD_ERROR: ModelLoadingException\n{str(err)}')
            warn = get_operator(Config.kt_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.PktModelProblem)
            return {'CANCELLED'}
        except TypeError as err:
            _log.error(f'ADD_HEAD_ERROR: TypeError\n{str(err)}')
            warn = get_operator(Config.kt_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.CannotCreateObject)
            return {'CANCELLED'}
        except Exception as err:
            _log.error(f'ADD_HEAD_ERROR: Exception\n{str(err)}')
            warn = get_operator(Config.kt_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.PktProblem)
            return {'CANCELLED'}

        attrs.add_to_fb_collection(obj)  # link to FB objects collection
        loader.set_keentools_attributes(obj)

        center_viewports_on_object(obj)

        # bpy.ops.object.shade_smooth()
        h = settings.heads.add()
        h.headobj = obj
        h.reset_sensor_size()

        settings.current_headnum = settings.get_last_headnum()
        loader.save_fb_serial_and_image_pathes(settings.current_headnum)

        show_ui_panel(context)

        _log.output('HEAD HAS BEEN SUCCESSFULLY CREATED')
        _log.output(f'{self.__class__.__name__} end >>>')
        return {'FINISHED'}

    @classmethod
    def new_head(cls):
        _log.yellow('new_head')
        settings = fb_settings()
        mesh = settings.loader().universal_mesh_loader(FBConfig.default_fb_mesh_name)
        _log.output('bpy_create_object')
        obj = bpy_create_object(FBConfig.default_fb_object_name, mesh)
        _log.output('new_head end >>>')
        return obj
