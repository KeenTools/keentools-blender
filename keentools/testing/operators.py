# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2023  KeenTools

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

from typing import Any, Optional, Tuple, List
import numpy as np

import bpy
from bpy.types import Operator
from bpy.props import StringProperty

from ..utils.kt_logging import KTLogger
from ..addon_config import Config
from ..geotracker.gtloader import GTLoader
from ..facebuilder.fbloader import FBLoader
from ..utils.bpy_common import (bpy_remove_object,
                                bpy_create_object,
                                bpy_link_to_scene,
                                bpy_scene_camera)
from ..utils.mesh_builder import build_geo


_log = KTLogger(__name__)


def test_points2d(points2d: Any, *,
                  x_step: float=30, y_step: float=20,
                  x_start: float=30, y_start: float=30,
                  point_count: int=5) -> None:
    verts: List[Tuple] = []
    vert_colors: List[Tuple] = []
    colors = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0),
              (0, 1, 1), (1, 0, 1), (0, 0, 0), (1, 1, 1)]
    for i, col in enumerate(colors):
        for x in range(point_count):
            verts.append((x_start + x * x_step, y_start + y_step * i))
            vert_colors.append((*col, (x + 1)/point_count))
    points2d.set_vertices_and_colors(np.array(verts, dtype=np.float32),
                                     np.array(vert_colors, dtype=np.float32))
    points2d.create_batch()


def test_points3d(points3d: Any, *,
                  x_step: float=0.3, y_step: float=0.2,
                  x_start: float=0, y_start: float=0,
                  point_count: int=10) -> None:
    verts: List[Tuple] = []
    vert_colors: List[Tuple] = []
    colors = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0),
              (0, 1, 1), (1, 0, 1), (0, 0, 0), (1, 1, 1)]
    for i, col in enumerate(colors):
        for x in range(point_count):
            verts.append((x_start + x * x_step, y_start + y_step * i, 0))
            vert_colors.append((*col, (x + 1)/point_count))
    points3d.set_vertices_and_colors(np.array(verts, dtype=np.float32),
                                     np.array(vert_colors, dtype=np.float32))
    points3d.create_batch()


def test_edges_3d(residuals: Any, *,
                  x_step: float=0.3, y_step: float=0.2,
                  x_start: float=0, y_start: float=0,
                  point_count: int=10) -> None:
    verts: List[Tuple] = []
    vert_colors: List[Tuple] = []
    edge_lengths: List[float] = []
    colors = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0),
              (0, 1, 1), (1, 0, 1), (0, 0, 0), (1, 1, 1)]
    for i, col in enumerate(colors):
        for x in range(point_count):
            verts.append((x_start + x * x_step, y_start + y_step * i, 0))
            verts.append((x_start + x * x_step, y_start + y_step * i, 0.5))
            vert_colors.append((*col, (x + 1)/point_count))
            vert_colors.append((*col, (x + 1)/point_count))
            edge_lengths.append(0)
            edge_lengths.append(22.0)
    residuals.set_vertices_and_colors(np.array(verts, dtype=np.float32),
                                      np.array(vert_colors, dtype=np.float32))
    residuals.lengths = np.array(edge_lengths, dtype=np.float32)
    residuals.create_batch()


def test_residuals(residuals: Any, *,
                   x_step: float=30, y_step: float=20,
                   x_start: float=30, y_start: float=30,
                   point_count: int=6) -> None:
    verts: List[Tuple] = []
    vert_colors: List[Tuple] = []
    edge_lengths: List[float] = []
    colors = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0),
          (0, 1, 1), (1, 0, 1), (0, 0, 0), (1, 1, 1)]
    for i, col in enumerate(colors):
        for x in range(point_count):
            verts.append((x_start + x * x_step, y_start + y_step * i))
            verts.append((30 + x_start + x * x_step, 30 + y_start + y_step * i))
            vert_colors.append((*col, (x + 1)/point_count))
            vert_colors.append((*col, (x + 1)/point_count))
            edge_lengths.append(0)
            edge_lengths.append(22.0)
    residuals.set_vertices_and_colors(np.array(verts, dtype=np.float32),
                                      np.array(vert_colors, dtype=np.float32))
    residuals.edge_lengths = np.array(edge_lengths, dtype=np.float32)
    residuals.create_batch()


def test_wireframe(wireframer: Any, *, obj: Any=None,
                   normals: bool=False, lit_wireframe: bool=False) -> None:
    if not obj:
        return
    camera = bpy_scene_camera()
    wireframer.init_geom_data_from_mesh(obj)
    wireframer.set_object_world_matrix(obj.matrix_world)
    wireframer.set_camera_pos(obj.matrix_world, camera.matrix_world)
    if normals:
        geo = build_geo(obj, get_uv=True)
        wireframer.init_geom_data_from_core(*GTLoader.get_geo_shader_data(
                                            geo, obj.matrix_world))
    wireframer.init_color_data((0, 1, 0, 0.5))
    wireframer.set_adaptive_opacity(1.0)
    wireframer.set_backface_culling(True)
    wireframer.set_lit_wireframe(lit_wireframe)
    wireframer.create_batches()


def test_selection(selector: Any, *,
                   left: Tuple[float, float]=(20, 20),
                   right: Tuple[float, float]=(300, 120)) -> None:
    selector.clear_rectangle()
    selector.add_rectangle(*left, *right)
    selector.create_batch()


def create_np_mask_image(*, width: int=512, height: int=256,
                         channels: int=4) -> Any:
    black_color = (0, 0, 0, 1)
    white_color = (1, 1, 1, 1)
    np_buf = np.full((height, width, channels), white_color, dtype=np.float32)
    r = 100
    r2 = r * r
    xc = width / 2
    yc = height / 2
    for x in range(width):
        for y in range(height):
            if (x - xc) ** 2 + (y - yc) ** 2 < r2:
                np_buf[y, x] = black_color
    return np_buf


def create_bpy_mask_image(*, name: str = 'test_image',
                          width: int = 512, height: int = 256,
                          channels: int = 4) -> Any:
    np_buf = create_np_mask_image(width=width, height=height,
                                  channels=channels)
    img = bpy.data.images.new(name, width=width, height=height,
                              alpha=True, float_buffer=False)
    img.pixels[:] = np_buf.ravel()
    return img


def test_mask2d(mask2d: Any, *, width: int=512, height: int=256,
                left: Tuple[float, float]=(20, 220)) -> None:
    img = create_bpy_mask_image(width=width, height=height)
    mask2d.image = img
    mask2d.left = left
    mask2d.right = (left[0] + width, left[1] + height)
    mask2d.create_batch()


def test_timeliner(timeliner: Any) -> None:
    timeliner.set_keyframes([x * 10 for x in range(26)])
    timeliner.create_batch()
    GTLoader.update_all_timelines()


def gt_points2d(area: Any) -> None:
    vp = GTLoader.viewport()
    points2d = vp.points2d()
    points2d.register_handler(area=area)
    test_points2d(points2d)


def fb_points2d(area: Any) -> None:
    vp = FBLoader.viewport()
    points2d = vp.points2d()
    points2d.register_handler(area=area)
    test_points2d(points2d)


def gt_points3d(area: Any) -> None:
    vp = GTLoader.viewport()
    points3d = vp.points3d()
    points3d.register_handler(area=area)
    test_points3d(points3d)


def fb_points3d(area: Any) -> None:
    vp = FBLoader.viewport()
    points3d = vp.points3d()
    points3d.register_handler(area=area)
    test_points3d(points3d)


def gt_residuals(area: Any) -> None:
    vp = GTLoader.viewport()
    residuals = vp.residuals()
    residuals.register_handler(area=area)
    test_residuals(residuals)


def fb_residuals(area: Any) -> None:
    vp = FBLoader.viewport()
    residuals = vp.residuals()
    residuals.register_handler(area=area)
    test_residuals(residuals)


def gt_wireframer(area: Any) -> None:
    vp = GTLoader.viewport()
    wireframer = vp.wireframer()
    wireframer.register_handler(area=area)
    bpy.ops.mesh.primitive_monkey_add(size=4.0)
    obj = bpy.context.object
    test_wireframe(wireframer, obj=obj, normals=True, lit_wireframe=True)
    bpy_remove_object(obj)


def fb_wireframer(area: Any) -> None:
    mesh = FBLoader.universal_mesh_loader('test_head_mesh')
    obj = bpy_create_object('test_head', mesh)
    bpy_link_to_scene(obj)
    obj.matrix_world[0][0] = 3.0
    obj.matrix_world[1][1] = 3.0
    obj.matrix_world[2][2] = 3.0

    fb = FBLoader.get_builder()

    vp = FBLoader.viewport()
    geo = fb.applied_args_model()

    wireframer = vp.wireframer()
    wireframer.init_edge_indices()
    wireframer.init_geom_data_from_core(*FBLoader.get_geo_shader_data(geo))
    wireframer.init_colors((*Config.fb_color_schemes['white'],
                            Config.fb_midline_color), 0.5)
    wireframer.init_wireframe_image(True)
    bpy_remove_object(obj)
    wireframer.create_batches()
    wireframer.register_handler(area=area)
    _log.output('FB wireframer statistics:' + wireframer.get_statistics())


def gt_selector(area: Any) -> None:
    vp = GTLoader.viewport()
    selector = vp.selector()
    selector.register_handler(area=area)
    test_selection(selector)


def fb_rectangler(area: Any) -> None:
    vp = FBLoader.viewport()
    rectangler = vp.rectangler()
    rectangler.clear_rectangles()
    rectangler.register_handler(area=area)
    rectangler.add_rectangle(0, 0, 150, 100, 300, 200, (1, 0, 0, 1))
    rectangler.prepare_shader_data(area)
    rectangler.create_batch()


def gt_rectangler(area: Any) -> None:
    vp = GTLoader.viewport()
    rectangler = vp.rectangler()
    rectangler.clear_rectangles()
    rectangler.register_handler(area=area)
    rectangler.add_rectangle(0, 0, 160, 110, 300, 200, (1, 0, 1, 1))
    rectangler.prepare_shader_data(area)
    rectangler.create_batch()


def gt_texter(area: Any, *, text: str='Test GT shaders',
              description: str='Description for current operation') -> None:
    vp = GTLoader.viewport()
    texter = vp.texter()
    texter.register_handler(area=area)
    vp.message_to_screen(
        [{'text': text,
          'y': 60, 'color': (1.0, 0.0, 0.0, 0.7)},
         {'text': description,
          'y': 30, 'color': (1.0, 1.0, 1.0, 0.7)}]
    )


def fb_texter(area: Any, *, text: str='Test FB shaders',
              description: str='Description for current operation') -> Any:
    vp = FBLoader.viewport()
    texter = vp.texter()
    texter.register_handler(area=area)
    vp.message_to_screen(
        [{'text': text,
          'y': 60, 'color': (1.0, 0.0, 0.0, 0.7)},
         {'text': description,
          'y': 30, 'color': (1.0, 1.0, 1.0, 0.7)}]
    )


def gt_mask2d(area: Any) -> None:
    vp = GTLoader.viewport()
    mask2d = vp.mask2d()
    mask2d.register_handler(area=area)
    test_mask2d(mask2d)


def gt_timeliner() -> None:
    vp = GTLoader.viewport()
    timeliner = vp.timeliner()
    timeliner.register_handler()
    test_timeliner(timeliner)


def gt_stop_all() -> None:
    vp = GTLoader.viewport()
    vp.points2d().unregister_handler()
    vp.points3d().unregister_handler()
    vp.residuals().unregister_handler()
    vp.wireframer().unregister_handler()
    vp.rectangler().unregister_handler()
    vp.selector().unregister_handler()
    vp.mask2d().unregister_handler()
    vp.timeliner().unregister_handler()
    GTLoader.update_all_timelines()
    vp.texter().unregister_handler()


def fb_stop_all() -> None:
    FBLoader.stop_viewport()


def gt_load_all_shaders() -> None:
    vp = GTLoader.viewport()
    if not vp.load_all_shaders():
        assert False, 'GT Shader loading problem'
    vp.unhide_all_shaders()


def fb_load_all_shaders(area: Any) -> None:
    vp = FBLoader.viewport()
    if not vp.load_all_shaders():
        assert False, 'FB Shader loading problem'
    vp.unhide_all_shaders()


class GTShaderTestOperator(Operator):
    bl_idname = Config.kt_gt_shader_testing_idname
    bl_label = 'Run Test'
    bl_options = {'REGISTER'}
    bl_description = 'Start test'

    action: StringProperty(name='Action Name')

    def draw(self, context):
        pass

    def execute(self, context):
        area = context.area

        gt_load_all_shaders()

        if self.action == 'points2d':
            gt_points2d(area=area)
        elif self.action == 'points3d':
            gt_points3d(area=area)
        elif self.action == 'residuals':
            gt_residuals(area=area)
        elif self.action == 'wireframer':
            gt_wireframer(area=area)
        elif self.action == 'rectangler':
            gt_rectangler(area=area)
        elif self.action == 'selector':
            gt_selector(area=area)
        elif self.action == 'mask2d':
            gt_mask2d(area=area)
        elif self.action == 'timeliner':
            gt_timeliner()
        elif self.action == 'texter':
            gt_texter(area=area)
        elif self.action == 'all':
            gt_points2d(area=area)
            gt_points3d(area=area)
            gt_residuals(area=area)
            gt_wireframer(area=area)
            gt_rectangler(area=area)
            gt_selector(area=area)
            gt_mask2d(area=area)
            gt_timeliner()
            gt_texter(area=area)
        elif self.action == 'stop':
            gt_stop_all()
        context.area.tag_redraw()
        return {'FINISHED'}


class FBShaderTestOperator(Operator):
    bl_idname = Config.kt_fb_shader_testing_idname
    bl_label = 'Run Test'
    bl_options = {'REGISTER'}
    bl_description = 'Start test'

    action: StringProperty(name='Action Name')

    def draw(self, context):
        pass

    def execute(self, context):
        area = context.area

        fb_load_all_shaders(area)

        if self.action == 'points2d':
            fb_points2d(area)
        elif self.action == 'points3d':
            fb_points3d(area)
        elif self.action == 'residuals':
            fb_residuals(area)
        elif self.action == 'wireframer':
            fb_wireframer(area)
        elif self.action == 'rectangler':
            fb_rectangler(area)
        elif self.action == 'texter':
            fb_texter(area)
        elif self.action == 'all':
            fb_points2d(area)
            fb_points3d(area)
            fb_residuals(area)
            fb_wireframer(area)
            fb_rectangler(area)
            fb_texter(area)
        elif self.action == 'stop':
            fb_stop_all()

        area.tag_redraw()
        return {'FINISHED'}
