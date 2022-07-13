import logging
import bpy

from ..addon_config import Config, get_operator, ErrorType
from ..geotracker_config import GTConfig, get_gt_settings
from .gtloader import GTLoader
from ..utils import coords
from ..utils.animation import create_locrot_keyframe, insert_keyframe_in_fcurve
from ..blender_independent_packages.pykeentools_loader import module as pkt_module
from ..utils.manipulate import force_undo_push


class GT_OT_MovePin(bpy.types.Operator):
    bl_idname = GTConfig.gt_movepin_idname
    bl_label = 'GeoTracker MovePin operator'
    bl_description = 'Operator MovePin'
    bl_options = {'REGISTER'}

    test_action: bpy.props.StringProperty(default="")

    pinx: bpy.props.FloatProperty(default=0)
    piny: bpy.props.FloatProperty(default=0)

    new_pin_flag: bpy.props.BoolProperty(default=False)

    def _move_pin_mode_on(self):
        settings = get_gt_settings()
        settings.move_pin_mode = True

    def _move_pin_mode_off(self):
        settings = get_gt_settings()
        settings.move_pin_mode = False

    def _before_operator_finish(self):
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not GTConfig.use_storage:
            create_locrot_keyframe(geotracker.animatable_object(), 'KEYFRAME')
        self._move_pin_mode_off()

    def _new_pin(self, area, mouse_x, mouse_y):
        logger = logging.getLogger(__name__)
        log_output = logger.debug
        settings = get_gt_settings()

        frame = settings.current_frame()
        x, y = coords.get_image_space_coord(mouse_x, mouse_y, area)

        pin = GTLoader.add_pin(
            frame, (coords.image_space_to_frame(x, y))
        )
        log_output(f'_new_pin pin: {pin}')
        if pin is not False:
            vp = GTLoader.viewport()
            vp.pins().add_pin((x, y))
            vp.pins().set_current_pin_num_to_last()
            log_output(f'_new_pin ADD PIN pins: {vp.pins().arr()}')
            return True
        else:
            logger.debug('MISS MODEL')
            GTLoader.viewport().pins().reset_current_pin()
            return False

    def _auto_keyframe_add(self):
        settings = get_gt_settings()
        keyframe = settings.current_frame()
        gt = GTLoader.kt_geotracker()
        if not gt.is_key_at(keyframe):
            mat = GTLoader.calc_model_matrix()
            gt.set_keyframe(keyframe, mat)
            return True
        return False

    def _remove_keyframe(self):
        settings = get_gt_settings()
        keyframe = settings.current_frame()
        gt = GTLoader.kt_geotracker()
        if gt.is_key_at(keyframe):
            gt.remove_keyframe(keyframe)

    def init_action(self, context, mouse_x, mouse_y):
        logger = logging.getLogger(__name__)
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker or not geotracker.geomobj or not geotracker.camobj:
            return False

        new_keyframe_flag = self._auto_keyframe_add()
        self.new_pin_flag = False

        vp = GTLoader.viewport()
        vp.update_view_relative_pixel_size(context.area)

        GTLoader.load_pins_into_viewport()

        x, y = coords.get_image_space_coord(mouse_x, mouse_y, context.area)
        vp.pins().set_current_pin((x, y))

        nearest, dist2 = coords.nearest_point(x, y, vp.pins().arr())

        if nearest >= 0 and dist2 < vp.tolerance_dist2():
            logger.debug('PIN FOUND: {}'.format(nearest))
            vp.pins().set_current_pin_num(nearest)
        else:
            self.new_pin_flag = self._new_pin(context.area, mouse_x, mouse_y)
            if not self.new_pin_flag:
                if new_keyframe_flag:
                    self._remove_keyframe()
                return False

        vp.create_batch_2d(context.area)
        vp.register_handlers(context)
        return True

    def on_left_mouse_release(self, area, event):
        mouse_x, mouse_y = event.mouse_region_x, event.mouse_region_y

        x, y = coords.get_image_space_coord(mouse_x, mouse_y, area)
        vp = GTLoader.viewport()
        pins = vp.pins()
        if pins.current_pin() is not None:
            # Move current 2D-pin
            pins.arr()[pins.current_pin_num()] = (x, y)
        pins.reset_current_pin()

        GTLoader.spring_pins_back()
        GTLoader.save_geotracker()

        GTLoader.update_all_viewport_shaders(area)
        self._before_operator_finish()
        vp.tag_redraw()

        if self.new_pin_flag:
            force_undo_push('Add GeoTracker pin')
            self.new_pin_flag = False
        else:
            force_undo_push('Drag GeoTracker pin')
        return {'FINISHED'}

    @staticmethod
    def _pin_drag(kid, area, mouse_x, mouse_y):
        x, y = coords.get_image_space_coord(mouse_x, mouse_y, area)
        pins = GTLoader.viewport().pins()
        pins.set_current_pin((x, y))
        pin_idx = pins.current_pin_num()
        pins.arr()[pin_idx] = (x, y)
        GTLoader.move_pin(kid, pin_idx, (x, y))

    def on_mouse_move(self, area, mouse_x, mouse_y):
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return self.on_default_modal()

        frame = settings.current_frame()
        self._pin_drag(frame, area, mouse_x, mouse_y)

        if not GTLoader.solve():
            self._before_operator_finish()
            return {'FINISHED'}

        GTLoader.place_camera()
        if geotracker.focal_length_estimation:
            focal = GTLoader.updated_focal_length()
            if focal is not None:
                camobj = geotracker.camobj
                if not GTConfig.use_storage:
                    insert_keyframe_in_fcurve(camobj.data, frame, focal,
                                              keyframe_type='KEYFRAME',
                                              data_path='lens', index=0)
                    camobj.data.lens = focal

        vp = GTLoader.viewport()
        gt = GTLoader.kt_geotracker()
        vp.update_surface_points(gt, geotracker.geomobj, frame)

        if not geotracker.camera_mode():
            wf = vp.wireframer()
            wf.init_geom_data_from_mesh(geotracker.geomobj)
            wf.create_batches()

        vp.create_batch_2d(area)
        vp.update_residuals(gt, area, frame)
        vp.tag_redraw()
        return self.on_default_modal()

    def on_default_modal(self):
        logger = logging.getLogger(__name__)
        if GTLoader.viewport().pins().current_pin() is not None:
            return {'RUNNING_MODAL'}
        else:
            logger.debug('MOVE PIN FINISH')
            self._before_operator_finish()
            return {'FINISHED'}

    def invoke(self, context, event):
        logger = logging.getLogger(__name__)
        log_output = logger.debug
        if not self.init_action(context,
                                event.mouse_region_x, event.mouse_region_y):
            settings = get_gt_settings()
            settings.start_selection(event.mouse_region_x, event.mouse_region_y)
            logger.debug('START SELECTION')
            return {'CANCELLED'}

        self._move_pin_mode_on()
        GTLoader.viewport().create_batch_2d(context.area)
        context.window_manager.modal_handler_add(self)
        log_output('GT START PIN MOVING')
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        logger = logging.getLogger(__name__)
        mouse_x = event.mouse_region_x
        mouse_y = event.mouse_region_y

        if event.value == 'RELEASE' and event.type == 'LEFTMOUSE':
            logger.debug('LEFT MOUSE RELEASE')
            return self.on_left_mouse_release(context.area, event)

        if event.type == 'MOUSEMOVE' \
                and GTLoader.viewport().pins().current_pin() is not None:
            logger.debug('MOUSEMOVE {} {}'.format(mouse_x, mouse_y))
            return self.on_mouse_move(context.area, mouse_x, mouse_y)

        return self.on_default_modal()
