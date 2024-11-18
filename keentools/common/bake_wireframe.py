import numpy as np
from typing import Any, List, Optional, Tuple

from bpy.types import Object, Area, SpaceView3D
import gpu

from ..utils.kt_logging import KTLogger
from ..addon_config import Config, get_settings, get_operator, ProductType
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
from ..utils.polygons import KTRasterImage
from ..utils.images import get_background_image_strict, inverse_gamma_color
from ..geotracker.utils.prechecks import prepare_camera


_log = KTLogger(__name__)


_bake_generator_var: Optional[Any] = None
_gt_wireframer: Optional[Any] = None
_ft_wireframer: Optional[Any] = None
_background_shader: Optional[Any] = None


class LitWireframeRenderer(KTLitEdgeShaderLocal3D):
    def __init__(self):
        super().__init__(target_class=SpaceView3D, mask_color=(1, 0, 0, 1))
        self.background: Any = KTRasterImage(target_class=SpaceView3D)

    def init_shaders(self) -> Optional[bool]:
        if not super().init_shaders():
            return False
        return self.background.init_shaders()

    def create_batches(self) -> None:
        _log.red(f'{self.__class__.__name__}.create_batches start')
        super().create_batches()
        self.background.create_batch()
        _log.output(f'{self.__class__.__name__}.create_batches end >>>')

    def draw_main(self) -> None:
        set_depth_test('NONE')
        self.background.draw_main()

        set_depth_test('LESS_EQUAL')
        set_depth_mask(True)
        set_color_mask(False, False, False, False)
        self.draw_empty_fill()

        set_depth_mask(False)
        set_color_mask(True, True, True, True)
        set_blend_alpha()
        self.draw_edges()

        revert_blender_viewport_state()


def get_FaceLitWireframeRenderer() -> Any:
    from ..facetracker.edges import FTRasterEdgeShader3D
    class FaceLitWireframeRenderer(FTRasterEdgeShader3D):
        def __init__(self):
            super().__init__(target_class=SpaceView3D)
            self.background: Any = KTRasterImage(target_class=SpaceView3D)

        def init_shaders(self) -> Optional[bool]:
            if not super().init_shaders():
                return False
            return self.background.init_shaders()

        def create_batches(self) -> None:
            _log.red(f'{self.__class__.__name__}.create_batches start')
            super().create_batches()
            self.background.create_batch()
            _log.output(f'{self.__class__.__name__}.create_batches end >>>')

        def draw_main(self) -> None:
            set_depth_test('NONE')
            self.background.draw_main()

            set_depth_test('LESS_EQUAL')
            set_depth_mask(True)
            set_color_mask(False, False, False, False)
            self.draw_empty_fill()

            set_depth_mask(False)
            set_color_mask(True, True, True, True)
            set_blend_alpha()
            if not self.use_simple_shader:
                self._draw_textured_line()
            else:
                self._draw_simple_line()

            revert_blender_viewport_state()

    return FaceLitWireframeRenderer()


def get_wireframer(product: int) -> Any:
    if product == ProductType.GEOTRACKER:
        global _gt_wireframer
        if _gt_wireframer is None:
            _gt_wireframer = LitWireframeRenderer()
        return _gt_wireframer
    elif product == ProductType.FACETRACKER:
        global _ft_wireframer
        if _ft_wireframer is None:
            _ft_wireframer = get_FaceLitWireframeRenderer()
        return _ft_wireframer
    assert False, f'Wrong product type [{product}] in get_wireframer'


def get_background_shader() -> Any:
    global _background_shader
    if _background_shader is None:
        _background_shader = KTRasterImage(target_class=SpaceView3D)
    return _background_shader


def bake_generator(area: Area, geotracker: Any, filepath_pattern: str,
                   *, file_format: str = 'PNG', frames: List[int],
                   digits: int = 4, product: int, use_background: bool) -> Any:
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

        wireframer = get_wireframer(product)
        wireframer.viewport_size = (rx, ry)
        wireframer.init_geom_data_from_mesh(geomobj)
        wireframer.set_object_world_matrix(geomobj.matrix_world)
        wireframer.set_camera_pos(geomobj.matrix_world, camobj.matrix_world)

        geo = loader.get_geo()
        if product == ProductType.FACETRACKER:
            wireframer.init_edge_indices()
        wireframer.init_geom_data_from_core(
            *loader.get_geo_shader_data(geo, geomobj.matrix_world))

        wireframer.create_batches()
        wireframer.background.image = (None if not use_background else
                                       get_background_image_strict(camobj,
                                                                   index=0))
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
                            special_color: Tuple = (1., 0., 0., 1.0),
                            midline_color: Tuple = (1., 1., 0., 1.0),
                            lit_wireframe: bool = True,
                            backface_culling: bool = True,
                            use_background: bool = False) -> None:
    _log.yellow('bake_wireframe_sequence start')
    op = get_operator(Config.kt_interrupt_modal_idname)
    op('INVOKE_DEFAULT', product=product)

    global _bake_generator_var
    _bake_generator_var = bake_generator(area, geotracker,
                                         filepath_pattern,
                                         file_format=file_format,
                                         frames=frames, digits=digits,
                                         product=product,
                                         use_background=use_background)
    prepare_camera(area, product=product)
    settings = get_settings(product)
    vp = settings.loader().viewport()
    if not settings.pinmode:
        vp.texter().register_handler(area=area)

    wireframer = get_wireframer(product)
    wireframer.set_line_width(line_width)
    wireframer.init_shaders()
    if product == ProductType.GEOTRACKER:
        wireframer.init_color_data(inverse_gamma_color(list(line_color)))
    elif product == ProductType.FACETRACKER:
        wireframer.init_colors([inverse_gamma_color(list(line_color)),
                                inverse_gamma_color(list(special_color)),
                                inverse_gamma_color(list(midline_color))],
                               settings.wireframe_opacity)
        wireframer.init_wireframe_image(True)
    wireframer.set_lit_wireframe(lit_wireframe)
    wireframer.set_backface_culling(backface_culling)

    bpy_timer_register(_bake_caller, first_interval=0.0)
    _log.output('bake_wireframe_sequence end >>>')
