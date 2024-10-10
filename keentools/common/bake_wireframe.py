import numpy as np
from typing import Any, List, Optional, Tuple

from bpy.types import Object, Area, SpaceView3D
import gpu

from ..utils.kt_logging import KTLogger
from ..addon_config import Config, get_settings, get_operator
from ..utils.version import BVersion
from ..utils.bpy_common import (bpy_context,
                                bpy_set_current_frame,
                                bpy_render_frame,
                                bpy_timer_register)
from ..utils.mesh_builder import build_geo
from ..utils.images import (create_compatible_bpy_image,
                            assign_pixels_data,
                            remove_bpy_image)
from ..utils.ui_redraw import total_redraw_ui
from ..utils.localview import exit_area_localview
from ..geotracker.interface.screen_mesages import (revert_default_screen_message,
                                        single_line_screen_message,
                                        texture_projection_screen_message)
from ..utils.edges import KTLitEdgeShaderLocal3D
from ..utils.gpu_control import (set_blend_alpha,
                                 set_depth_test,
                                 set_depth_mask,
                                 set_color_mask,
                                 revert_blender_viewport_state)


_log = KTLogger(__name__)


_bake_generator_var: Optional[Any] = None
_wireframer: Optional[Any] = None


class LitWireframeRenderer(KTLitEdgeShaderLocal3D):
    def __init__(self):
        super().__init__(target_class=SpaceView3D, mask_color=(1, 0, 0, 1))

    def draw_main(self) -> None:
        set_depth_test('LESS_EQUAL')
        set_color_mask(False, False, False, False)
        self.draw_empty_fill()

        set_color_mask(True, True, True, True)
        set_depth_mask(False)
        set_blend_alpha()
        self.draw_edges()

        revert_blender_viewport_state()


def get_wireframer():
    global _wireframer
    if _wireframer is None:
        _wireframer = LitWireframeRenderer()
    return _wireframer


def bake_generator(area: Area, geotracker: Any, filepath_pattern: str,
                   *, file_format: str = 'PNG', frames: List[int],
                   digits: int = 4, product: int) -> Any:
    def _finish():
        settings.stop_calculating()
        revert_default_screen_message(unregister=not settings.pinmode,
                                      product=product)
        if tex is not None:
            remove_bpy_image(tex)
        if not settings.pinmode:
            settings.viewport_state.show_ui_elements(area)
            exit_area_localview(area)
        settings.user_interrupts = True
        total_redraw_ui()

    delta = 0.001
    settings = get_settings(product)
    settings.start_calculating('REPROJECT')

    single_line_screen_message('Wireframe baking… Please wait',
                               product=product)

    tex = None
    total_frames = len(frames)
    for num, frame in enumerate(frames):
        if settings.user_interrupts:
            _finish()
            return None

        texture_projection_screen_message(num + 1, total_frames, product=product)

        settings.user_percent = 100 * num / total_frames
        bpy_set_current_frame(frame)

        yield delta

        rx, ry = bpy_render_frame()
        offscreen = gpu.types.GPUOffScreen(rx, ry)
        context = bpy_context()
        camobj = geotracker.camobj
        geomobj = geotracker.geomobj
        view_matrix = camobj.matrix_world.inverted()
        projection_matrix = camobj.calc_matrix_camera(
            context.evaluated_depsgraph_get(), x=rx, y=ry)

        settings = get_settings(product)
        loader = settings.loader()

        wireframer = get_wireframer()
        wireframer.viewport_size = (rx, ry)
        wireframer.init_geom_data_from_mesh(geomobj)
        wireframer.set_object_world_matrix(geomobj.matrix_world)
        wireframer.set_camera_pos(geomobj.matrix_world, camobj.matrix_world)

        geo = build_geo(geomobj, get_uv=True)
        wireframer.init_geom_data_from_core(*loader.get_geo_shader_data(geo,
                                            geomobj.matrix_world))

        wireframer.create_batches()

        with offscreen.bind():
            set_depth_mask(True)
            set_depth_test('LESS')
            framebuffer = gpu.state.active_framebuffer_get()
            framebuffer.clear(color=(0.0, 0.0, 0.0, 0.0), depth=1.0)
            with gpu.matrix.push_pop():
                gpu.matrix.load_identity()
                gpu.matrix.load_matrix(view_matrix)
                gpu.matrix.load_projection_matrix(projection_matrix)

                wireframer.draw_main()
                buffer = framebuffer.read_color(0, 0, rx, ry, 4, 0, 'UBYTE')
                built_texture = np.array(buffer, dtype=np.float32)
            set_depth_mask(False)
            set_depth_test('NONE')

        offscreen.free()

        if tex is None:
            tex = create_compatible_bpy_image(built_texture)
        tex.filepath_raw = filepath_pattern.format(str(frame).zfill(digits))
        tex.file_format = file_format
        assign_pixels_data(tex.pixels, built_texture.T.ravel() / 255)
        tex.save()
        _log.info(f'TEXTURE SAVED: {tex.filepath}')

        yield delta

    _finish()
    return None


def _bake_caller() -> Optional[float]:
    global _bake_generator_var
    if _bake_generator_var is None:
        return None
    try:
        return next(_bake_generator_var)
    except StopIteration:
        _log.output('Wireframe sequence baking generator is over')
    _bake_generator_var = None
    return None


def bake_wireframe_sequence(area: Area, geotracker: Any, filepath_pattern: str,
                            *, file_format: str = 'PNG', frames: List[int],
                            digits: int = 4, product: int,
                            line_width: float = 1.0,
                            line_color: Tuple = (0., 1., 0., 1.0),
                            lit_wireframe: bool = True,
                            backface_culling: bool = True) -> None:
    _log.yellow('bake_wireframe_sequence start')
    op = get_operator(Config.kt_interrupt_modal_idname)
    op('INVOKE_DEFAULT', product=product)

    global _bake_generator_var
    _bake_generator_var = bake_generator(area, geotracker,
                                         filepath_pattern,
                                         file_format=file_format,
                                         frames=frames, digits=digits,
                                         product=product)
    settings = get_settings(product)
    vp = settings.loader().viewport()
    if not settings.pinmode:
        vp.texter().register_handler(area=area)

    wireframer = get_wireframer()
    wireframer.set_line_width(line_width)
    wireframer.init_shaders()
    wireframer.init_color_data(line_color)
    wireframer.set_lit_wireframe(lit_wireframe)
    wireframer.set_backface_culling(backface_culling)

    bpy_timer_register(_bake_caller, first_interval=0.0)
    _log.output('bake_wireframe_sequence end >>>')
