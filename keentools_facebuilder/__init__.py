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


bl_info = {
    "name": "KeenTools FaceBuilder Addon v.0.1k",
    "author": "KeenTools",
    "description": "Creates Head and Face geometry with a few reference photos",
    "blender": (2, 80, 0),
    "location": "View3D > Add > Mesh and View UI (press N to open panel)",
    "wiki_url": "https://keentools.io/",
    "warning": "",
    "category": "Add Mesh"
}


import bpy


def init_pykeentools():
    def configure_pykeentools():
        import os
        import sys
        base_dir = os.path.dirname(os.path.abspath(__file__))
        pykeentools_dir = os.path.join(base_dir, 'pykeentools')
        sys.path.append(pykeentools_dir)
        data_dir = os.path.join(base_dir, 'data')
        # if this is true data directory will be found by pykeentools
        assert(os.path.samefile(data_dir, os.path.join(pykeentools_dir, '../data')))

    configure_pykeentools()
    from importlib.util import find_spec  # valid for python >= 3.4
    pykeentools_spec = find_spec('pykeentools')
    pykeentools_found = pykeentools_spec is not None
    if not pykeentools_found:
        # TODO
        # print a detailed message for user
        print('failed to init pykeentools')


init_pykeentools()


from . panels import OBJECT_PT_FBPanel, WM_OT_FBAddonWarning
from . panels import OBJECT_PT_FBSettingsPanel, OBJECT_PT_FBColorsPanel
from . panels import OBJECT_PT_TBPanel
from . panels import FBFixMenu
from . head import MESH_OT_FBAddHead
# from . body import MESH_OT_FBAddBody
from . settings import FBCameraItem
from . settings import FBHeadItem
from . settings import FBSceneSettings
from . main_operator import OBJECT_OT_FBOperator
from . draw import OBJECT_OT_FBDraw
from . movepin import OBJECT_OT_FBMovePin
from . actor import OBJECT_OT_FBActor
from . addon_prefs import FBAddonPreferences
from . filedialog import OBJECT_OT_FBOpenFilebrowser
from . config import config


classes = (
    OBJECT_PT_FBPanel,
    WM_OT_FBAddonWarning,
    OBJECT_PT_FBColorsPanel,
    OBJECT_PT_TBPanel,
    MESH_OT_FBAddHead,
    # MESH_OT_FBAddBody,
    OBJECT_OT_FBOperator,
    FBCameraItem,
    FBHeadItem,
    FBSceneSettings,
    OBJECT_PT_FBSettingsPanel,
    OBJECT_OT_FBDraw,
    OBJECT_OT_FBMovePin,
    OBJECT_OT_FBActor,
    FBAddonPreferences,
    OBJECT_OT_FBOpenFilebrowser,
    FBFixMenu
)


def menu_func(self, context):
    self.layout.operator(MESH_OT_FBAddHead.bl_idname, icon='USER')
    # self.layout.operator(MESH_OT_FBAddBody.bl_idname, icon='ARMATURE_DATA')


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_mesh_add.append(menu_func)
    # Main addon settings variable creation
    setattr(bpy.types.Scene, config.addon_global_var_name,
            bpy.props.PointerProperty(type=FBSceneSettings))


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    bpy.types.VIEW3D_MT_mesh_add.remove(menu_func)
    # Delete addon settings
    delattr(bpy.types.Scene, config.addon_global_var_name)


if __name__ == "__main__":
    register()
