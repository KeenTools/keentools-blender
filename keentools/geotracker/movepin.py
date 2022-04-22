import logging
import bpy

from ..addon_config import Config, get_operator, ErrorType
from ..geotracker_config import GTConfig, get_gt_settings
from .gtloader import GTLoader
from ..utils import coords
from .utils.animation import create_locrot_keyframe, insert_keyframe_in_fcurve
from ..blender_independent_packages.pykeentools_loader import module as pkt_module


class GT_OT_MovePin(bpy.types.Operator):
    bl_idname = GTConfig.gt_movepin_idname
    bl_label = 'GeoTracker MovePin operator'
    bl_description = 'Operator MovePin'
    bl_options = {'REGISTER'}

    test_action: bpy.props.StringProperty(default="")

    pinx: bpy.props.FloatProperty(default=0)
    piny: bpy.props.FloatProperty(default=0)

    def _pin_move_mode_on(self):
        settings = get_gt_settings()
        settings.pin_move_mode = True

    def _pin_move_mode_off(self):
        settings = get_gt_settings()
        settings.pin_move_mode = False

    def _end_finished(self):
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        create_locrot_keyframe(geotracker.animatable_object(), 'KEYFRAME')
        self._pin_move_mode_off()
        return {'FINISHED'}

    def _end_cancelled(self):
        self._pin_move_mode_off()
        return {'CANCELLED'}

    def _new_pin(self, context, mouse_x, mouse_y):
        logger = logging.getLogger(__name__)
        settings = get_gt_settings()

        frame = settings.current_frame()

        x, y = coords.get_image_space_coord(mouse_x, mouse_y, context)

        pin = GTLoader.add_pin(
            frame, (coords.image_space_to_frame(x, y))
        )
        if pin is not False:
            logger.debug('ADD PIN: {}'.format(pin))
            vp = GTLoader.viewport()
            vp.pins().add_pin((x, y))
            vp.pins().set_current_pin_num_to_last()
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

        vp = GTLoader.viewport()
        vp.update_view_relative_pixel_size(context)

        GTLoader.load_pins_into_viewport()

        x, y = coords.get_image_space_coord(mouse_x, mouse_y, context)
        vp.pins().set_current_pin((x, y))

        nearest, dist2 = coords.nearest_point(x, y, vp.pins().arr())

        if nearest >= 0 and dist2 < vp.tolerance_dist2():
            logger.debug('PIN FOUND: {}'.format(nearest))
            vp.pins().set_current_pin_num(nearest)
        else:
            new_pin_flag = self._new_pin(context, mouse_x, mouse_y)
            if not new_pin_flag:
                if new_keyframe_flag:
                    self._remove_keyframe()
                return False

        vp.create_batch_2d(context)
        vp.register_handlers(context)
        return True


    def on_left_mouse_release(self, context, event):
        mouse_x, mouse_y = event.mouse_region_x, event.mouse_region_y

        x, y = coords.get_image_space_coord(mouse_x, mouse_y, context)
        vp = GTLoader.viewport()
        pins = vp.pins()
        if pins.current_pin() is not None:
            # Move current 2D-pin
            pins.arr()[pins.current_pin_num()] = (x, y)
        pins.reset_current_pin()

        GTLoader.spring_pins_back()
        GTLoader.save_geotracker()

        GTLoader.update_all_viewport_shaders(context)
        GTLoader.tag_redraw(context)
        return self._end_finished()

    @staticmethod
    def _pin_drag(kid, context, mouse_x, mouse_y):
        x, y = coords.get_image_space_coord(mouse_x, mouse_y, context)
        pins = GTLoader.viewport().pins()
        pins.set_current_pin((x, y))
        pin_idx = pins.current_pin_num()
        pins.arr()[pin_idx] = (x, y)
        GTLoader.move_pin(kid, pin_idx, (x, y))

    def on_mouse_move(self, context, mouse_x, mouse_y):
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return self.on_default_modal()

        frame = settings.current_frame()
        self._pin_drag(frame, context, mouse_x, mouse_y)

        try:
            GTLoader.solve(geotracker.focal_length_estimation)
        except pkt_module().UnlicensedException as err:
            logger = logging.getLogger(__name__)
            logger.error('on_mouse_move UnlicensedException: '
                         '{}'.format(str(err)))
            warn = get_operator(Config.kt_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.NoLicense)
            return self._end_finished()
        except Exception as err:
            logger = logging.getLogger(__name__)
            logger.error('on_mouse_move UNKNOWN EXCEPTION: '
                         '{}'.format(str(err)))
            self.report({'ERROR'}, 'Unknown error (see console window)')
            return self._end_finished()

        GTLoader.place_camera()
        if geotracker.focal_length_estimation:
            focal = GTLoader.updated_focal_length()
            if focal is not None:
                camobj = geotracker.camobj
                insert_keyframe_in_fcurve(camobj.data, frame, focal,
                                          keyframe_type='KEYFRAME',
                                          data_path='lens', index=0)
                camobj.data.lens = focal

        vp = GTLoader.viewport()
        gt = GTLoader.kt_geotracker()
        vp.update_surface_points(gt, geotracker.geomobj, frame)

        if not geotracker.solve_for_camera_mode():
            wf = vp.wireframer()
            wf.init_geom_data_from_mesh(geotracker.geomobj)
            wf.create_batches()

        vp.create_batch_2d(context)
        vp.update_residuals(gt, context, frame)
        GTLoader.tag_redraw(context)
        return self.on_default_modal()

    def on_default_modal(self):
        logger = logging.getLogger(__name__)
        if GTLoader.viewport().pins().current_pin() is not None:
            return {'RUNNING_MODAL'}
        else:
            logger.debug('MOVE PIN FINISH')
            return self._end_finished()

    def invoke(self, context, event):
        logger = logging.getLogger(__name__)
        if not self.init_action(context,
                                event.mouse_region_x, event.mouse_region_y):
            settings = get_gt_settings()
            settings.start_selection(event.mouse_region_x, event.mouse_region_y)
            logger.debug('START SELECTION')
            return {'CANCELLED'}

        self._pin_move_mode_on()
        GTLoader.viewport().create_batch_2d(context)
        context.window_manager.modal_handler_add(self)
        logger.debug('START PIN MOVING')
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        logger = logging.getLogger(__name__)
        mouse_x = event.mouse_region_x
        mouse_y = event.mouse_region_y

        if event.value == 'RELEASE' and event.type == 'LEFTMOUSE':
            logger.debug('LEFT MOUSE RELEASE')
            return self.on_left_mouse_release(context, event)

        if event.type == 'MOUSEMOVE' \
                and GTLoader.viewport().pins().current_pin() is not None:
            logger.debug('MOUSEMOVE {} {}'.format(mouse_x, mouse_y))
            return self.on_mouse_move(context, mouse_x, mouse_y)

        return self.on_default_modal()
