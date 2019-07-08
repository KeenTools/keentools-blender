import bpy
from pykeentools import UnlicensedException

from .config import config, get_main_settings, ErrorType, BuilderType
from .fbdebug import FBDebug
from .fbloader import FBLoader
from .utils import (
    FBCalc,
    FBStopTimer
)


class OBJECT_OT_FBDraw(bpy.types.Operator):
    """ On Screen Face Builder Draw Operator """
    bl_idname = config.fb_draw_operator_idname
    bl_label = "FaceBuilder Draw operator"
    bl_description = "Operator for in-Viewport drawing"
    bl_options = {'REGISTER', 'UNDO'}  # {'REGISTER', 'UNDO'}

    headnum: bpy.props.IntProperty(default=0)
    camnum: bpy.props.IntProperty(default=0)

    def invoke(self, context, event):
        args = (self, context)
        settings = get_main_settings()
        head = settings.heads[self.headnum]
        headobj = head.headobj

        if settings.pinmode:
            # We had to finish last operation
            if settings.current_headnum >= 0 and settings.current_camnum >= 0:
                FBLoader.out_pinmode(
                    context,
                    settings.current_headnum,
                    settings.current_camnum
                )
                print(
                    'DrawInvoke FORCE FINISH:',
                    settings.current_headnum,
                    settings.current_camnum
                )

        # Settings structure is broken
        if not settings.check_heads_and_cams():
            # Fix and Out
            heads_deleted, cams_deleted = settings.fix_heads()
            if heads_deleted == 0:
                # bpy.ops.wm.fb_addon_warning('INVOKE_DEFAULT', msg=1)
                warn = getattr(bpy.ops.wm, config.fb_warning_operator_callname)
                warn('INVOKE_DEFAULT', msg=ErrorType.SceneDamaged)
            return {'FINISHED'}

        # Current headnum & camnum in global settings object
        settings.current_headnum = self.headnum
        settings.current_camnum = self.camnum

        print(
            'DrawInvoke START:',
            settings.current_headnum,
            settings.current_camnum
        )
        # === Debug only ===
        FBDebug.add_event_to_queue(
            'PIN_MODE_START', (self.headnum, self.camnum),
            FBCalc.get_raw_camera_2d_data(context))
        # === Debug only ===

        FBLoader.load_all(self.headnum, self.camnum, False)

        FBLoader.create_batch_2d(context)
        FBLoader.register_handlers(args, context)

        context.window_manager.modal_handler_add(self)

        # Hide geometry
        headobj.hide_viewport = True
        FBLoader.hide_other_cameras(context, self.headnum, self.camnum)
        # Start our shader
        FBLoader.wireframer.init_geom_data(headobj)
        col = settings.wireframe_color
        FBLoader.wireframer.init_color_data(
            (col[0], col[1], col[2], settings.wireframe_opacity))

        # Only for FaceBuilder coloring face parts
        if FBLoader.get_builder_type() == BuilderType.FaceBuilder:
            FBLoader.wireframer.init_special_areas(
                (1.0 - col[0], 1.0 - col[1], 1.0 - col[2],
                 settings.wireframe_opacity))

        FBLoader.wireframer.create_batches()
        FBLoader.wireframer.register_handler(args)

        kid = FBLoader.keyframe_by_camnum(self.headnum, self.camnum)
        # Load 3D pins
        FBLoader.update_surface_points(headobj, kid)

        # Can start much more times when not out from pinmode
        FBStopTimer.start()
        settings.pinmode = True
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        scene = context.scene
        settings = get_main_settings()
        # settings.pinmode = True

        headnum = settings.current_headnum
        camnum = settings.current_camnum
        kid = FBLoader.keyframe_by_camnum(headnum, camnum)

        # Quit if Screen changed
        if context.area is None:  # Different operation Space
            FBLoader.out_pinmode(context, headnum, camnum)
            return {'FINISHED'}

        head = settings.heads[headnum]
        if not head.headobj.hide_viewport:
            head.headobj.hide_viewport = True

        # Pixel size in relative coords
        FBLoader.update_pixel_size(context)

        # Screen Update request
        if context.area:
            context.area.tag_redraw()

        # Quit if PinMode out
        if settings.force_out_pinmode:  # Move Pin problem by ex.
            FBLoader.out_pinmode(context, headnum, camnum)
            settings.force_out_pinmode = False
            # bpy.ops.wm.fb_addon_warning('INVOKE_DEFAULT', msg=0)
            warn = getattr(bpy.ops.wm, config.fb_warning_operator_callname)
            warn('INVOKE_DEFAULT', msg=ErrorType.NoLicense)
            return {'FINISHED'}

        # Quit when camera rotated by user
        if context.space_data.region_3d.view_perspective != 'CAMERA':
            FBLoader.out_pinmode(context, headnum, camnum)
            return {'FINISHED'}

        # Quit by ESC or ENTER pressed
        if event.type in {'ESC', 'RET'}:
            FBLoader.out_pinmode(context, headnum, camnum)
            return {'FINISHED'}

        if event.value == "PRESS":
            # Left mouse button pressed. Set Pin
            if event.type == "LEFTMOUSE":
                # === Debug only ===
                FBDebug.add_event_to_queue(
                    'DRAW_OPERATOR_PRESS_LEFTMOUSE',
                    FBCalc.get_mouse_coords(event, context),
                    FBCalc.get_raw_camera_2d_data(context))
                # === Debug only ===

                p = FBCalc.get_mouse_coords(event, context)

                if not FBCalc.is_in_area(context, p[0], p[1]):
                    # FBLoader.out_pinmode(context, self.headnum, self.camnum)
                    return {'PASS_THROUGH'}

                if FBCalc.is_safe_region(context, p[0], p[1]):
                    # === Debug only ===
                    FBDebug.add_event_to_queue(
                        'CALL_MOVE_PIN_OPERATOR',
                        FBCalc.get_mouse_coords(event, context),
                        FBCalc.get_raw_camera_2d_data(context))
                    # === Debug only ===

                    # Registered Operator call
                    op = getattr(
                        bpy.ops.object, config.fb_movepin_operator_callname)
                    op('INVOKE_DEFAULT',
                        headnum=headnum,
                        camnum=camnum,
                        pinx=p[0], piny=p[1])
                    # return {'INTERFACE'}
                    return {'PASS_THROUGH'}
                # return {'FINISHED'}
                # return {'RUNNING_MODAL'}
                return {'PASS_THROUGH'}

        if event.value == "PRESS":
            # Right mouse button pressed - delete Pin
            if event.type == "RIGHTMOUSE":
                # === Debug only ===
                FBDebug.add_event_to_queue(
                    'IN_DRAW_PRESS_RIGHTMOUSE',
                    FBCalc.get_mouse_coords(event, context),
                    FBCalc.get_raw_camera_2d_data(context))
                # === Debug only ===

                x, y = FBCalc.get_image_space_coord(
                    context,
                    FBCalc.get_mouse_coords(event, context)
                )
                nearest, dist2 = FBCalc.nearest_point(x, y, FBLoader.spins)
                if nearest >= 0 and dist2 < FBLoader.tolerance_dist2():
                    # Nearest pin found
                    fb = FBLoader.get_builder()
                    head = settings.heads[headnum]
                    headobj = head.headobj
                    # Delete pin
                    fb.remove_pin(kid, nearest)
                    del FBLoader.spins[nearest]
                    # Setup Rigidity only for FaceBuilder
                    if FBLoader.get_builder_type() == BuilderType.FaceBuilder:
                        fb.set_auto_rigidity(settings.check_auto_rigidity)
                        fb.set_rigidity(settings.rigidity)

                    try:
                        # Solver
                        fb.solve_for_current_pins(kid)
                    except UnlicensedException:
                        settings.force_out_pinmode = True
                        FBLoader.out_pinmode(context, headnum, camnum)
                        self.report({'INFO'}, "PIN MODE LICENSE EXCEPTION")
                        return {'FINISHED'}

                    camobj = head.cameras[camnum].camobj

                    kid = FBLoader.keyframe_by_camnum(headnum, camnum)
                    # Camera update
                    FBLoader.place_cameraobj(kid, camobj, headobj)

                    # Head Mesh update
                    FBCalc.update_head_mesh(fb, headobj)
                    # Update all cameras position
                    FBLoader.update_cameras(headnum)
                    # Save result
                    FBLoader.fb_save(headnum, camnum)
                    FBLoader.update_surface_points(headobj, kid)
                    # Shader update
                    FBLoader.wireframer.init_geom_data(headobj)
                    FBLoader.wireframer.create_batches()

                    # Indicators update
                    FBLoader.update_pins_count(headnum, camnum)
                    # Undo push
                    head.need_update = True
                    FBLoader.force_undo_push()
                    head.need_update = False

                FBLoader.create_batch_2d(context)
                # out to prevent click events
                return {"RUNNING_MODAL"}

        if head.need_update:
            # Undo was called so Model redraw is needed
            FBLoader.wireframer.init_geom_data(head.headobj)
            FBLoader.wireframer.create_batches()
            head.need_update = False
            # Hide geometry
            # head.headobj.hide_viewport = True

            # Reload pins
            FBLoader.load_all(headnum, camnum)
            FBLoader.update_surface_points(
                head.headobj, FBLoader.keyframe_by_camnum(headnum, camnum))
            # FBLoader.load_pins(self.camnum, scene)

            # === Debug only ===
            FBDebug.add_event_to_queue(
                'UNDO_CALLED', (FBCalc.get_mouse_coords(event, context)))
            FBDebug.add_event_to_queue(
                'FORCE_SNAPSHOT', (FBCalc.get_mouse_coords(event, context)))
            FBDebug.make_snapshot()
            # === Debug only ===

        FBLoader.create_batch_2d(context)

        if FBLoader.current_pin:
            return {"RUNNING_MODAL"}
        else:
            return {"PASS_THROUGH"}
        # return {"RUNNING_MODAL"}
        # return {'INTERFACE'}
