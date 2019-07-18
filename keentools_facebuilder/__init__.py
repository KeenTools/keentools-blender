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
    "name": "KeenTools FaceBuilder Addon v.0.1m",
    "author": "KeenTools",
    "description": "Creates Head and Face geometry with a few reference photos",
    "blender": (2, 80, 0),
    "location": "View3D > Add > Mesh and View UI (press N to open panel)",
    "wiki_url": "https://www.keentools.io/facebuilder",
    "tracker_url": "https://www.keentools.io/contact",
    "warning": "",
    "category": "Add Mesh"
}


import bpy
import os
import sys
import tempfile
import shutil


def init_pykeentools_copy():
    win_file_name = "pykeentools.cp37-win_amd64.pyd"
    dir_name = 'keentools_fb'

    base_dir = os.path.dirname(os.path.abspath(__file__))
    pykeentools_dir = os.path.join(base_dir, 'pykeentools')
    data_dir = os.path.join(base_dir, 'data')
    src_path = os.path.join(pykeentools_dir, win_file_name)

    temp_dir = tempfile.gettempdir()

    if os.path.exists(src_path):
        # It's Win, so we need copy
        tmp_dir = os.path.join(temp_dir, dir_name)
        try:
            # Create default folder
            if not os.path.exists(tmp_dir):
                os.mkdir(tmp_dir)
            temp_path = os.path.join(tmp_dir, win_file_name)
            shutil.copy2(src_path, temp_path)
            pykeentools_dir = tmp_dir
            print("DEFAULT COPY CREATED")
            print("TMP_DIR", tmp_dir)
        except:
            print("CAN'T CREATE DEFAULT COPY")
            try:
                # Create temporary folder
                tmp_dir = tempfile.mkdtemp(prefix='keentools_fb_')  # new dir
                temp_path = os.path.join(tmp_dir, win_file_name)
                shutil.copy2(src_path, temp_path)
                pykeentools_dir = tmp_dir
                print("TEMPORARY COPY CREATED")
                print("TMP_DIR", tmp_dir)
            except:
                print("CAN'T CREATE TEMPORARY COPY")

    print("BASE_DIR", base_dir)
    print("DATA_DIR", data_dir)
    print("TEMP_DIR", temp_dir)
    print("PYKEENTOOLS_DIR", pykeentools_dir)

    os.environ["KEENTOOLS_DATA_PATH"] = data_dir  # "../data"
    # print("OS_ENV", os.environ)

    if pykeentools_dir not in sys.path:
        sys.path.append(pykeentools_dir)

    from importlib.util import find_spec  # valid for python >= 3.4
    pykeentools_spec = find_spec('pykeentools')
    print("PYKEENTOOLS_SPEC", pykeentools_spec)
    pykeentools_found = pykeentools_spec is not None
    if not pykeentools_found:
        # TODO
        # print a detailed message for user
        print('failed to init pykeentools')


init_pykeentools_copy()


from . panels import (OBJECT_PT_FBPanel, OBJECT_PT_FBFaceParts,
                      WM_OT_FBAddonWarning, OBJECT_PT_FBSettingsPanel,
                      OBJECT_PT_FBColorsPanel, OBJECT_PT_TBPanel,
                      OBJECT_MT_FBFixMenu)
from . head import MESH_OT_FBAddHead
from . body import MESH_OT_FBAddBody
from . settings import FBCameraItem
from . settings import FBHeadItem
from . settings import FBSceneSettings
from . main_operator import (OBJECT_OT_FBSelectCamera, OBJECT_OT_FBCenterGeo,
                             OBJECT_OT_FBUnmorph, OBJECT_OT_FBRemovePins,
                             OBJECT_OT_FBWireframeColor,
                             OBJECT_OT_FBFilterCameras, OBJECT_OT_FBFixSize,
                             OBJECT_OT_FBDeleteCamera, OBJECT_OT_FBAddCamera,
                             OBJECT_OT_FBAddonSettings,
                             OBJECT_OT_FBBakeTexture, OBJECT_OT_FBShowTexture)
from . draw import OBJECT_OT_FBDraw
from . movepin import OBJECT_OT_FBMovePin
from . actor import OBJECT_OT_FBActor
from . addon_prefs import FBAddonPreferences
from . filedialog import WM_OT_FBOpenFilebrowser
from . config import config


classes = (
    OBJECT_PT_FBPanel,
    OBJECT_PT_FBFaceParts,
    OBJECT_PT_FBColorsPanel,
    OBJECT_PT_TBPanel,
    OBJECT_MT_FBFixMenu,
    WM_OT_FBAddonWarning,
    MESH_OT_FBAddHead,
    MESH_OT_FBAddBody,
    OBJECT_OT_FBSelectCamera,
    OBJECT_OT_FBCenterGeo,
    OBJECT_OT_FBUnmorph,
    OBJECT_OT_FBRemovePins,
    OBJECT_OT_FBWireframeColor,
    OBJECT_OT_FBFilterCameras,
    OBJECT_OT_FBDeleteCamera,
    OBJECT_OT_FBAddCamera,
    OBJECT_OT_FBFixSize,
    OBJECT_OT_FBAddonSettings,
    OBJECT_OT_FBBakeTexture,
    OBJECT_OT_FBShowTexture,
    FBCameraItem,
    FBHeadItem,
    FBSceneSettings,
    OBJECT_PT_FBSettingsPanel,
    OBJECT_OT_FBDraw,
    OBJECT_OT_FBMovePin,
    OBJECT_OT_FBActor,
    FBAddonPreferences,
    WM_OT_FBOpenFilebrowser
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
