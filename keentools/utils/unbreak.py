from typing import Any, List

from bpy.types import Object

from .kt_logging import KTLogger
from ..addon_config import (ActionStatus,
                            ProductType,
                            product_name,
                            get_settings,
                            get_addon_preferences)
from .animation import (get_action,
                        get_object_keyframe_numbers,
                        mark_selected_points_in_locrot)
from ..geotracker.utils.tracking import (unbreak_rotation,
                                         check_unbreak_rotaion_is_needed)


_log = KTLogger(__name__)


def unbreak_rotation_with_status(obj: Object, frame_list: List) -> ActionStatus:
    if not obj:
        return ActionStatus(False, 'No object to unbreak rotation')

    if check_unbreak_rotaion_is_needed(obj):
        _log.output(f'{obj} needs for Unbreak Rotation!')

    action = get_action(obj)
    if action is None:
        msg = 'Selected object has no animation action'
        _log.error(msg)
        return ActionStatus(False, msg)

    if len(frame_list) < 2:
        msg = 'Not enough keys to apply Unbreak Rotation'
        _log.error(msg)
        return ActionStatus(False, msg)

    if not unbreak_rotation(obj, frame_list):
        msg = 'Unbreak Rotation was not applied'
        _log.error(msg)
        return ActionStatus(False, msg)

    return ActionStatus(True, 'ok')


def unbreak_object_rotation_act(obj: Object) -> ActionStatus:
    if not obj:
        return ActionStatus(False, 'No object to unbreak rotation')
    frame_list = get_object_keyframe_numbers(obj, loc=False, rot=True)
    return unbreak_rotation_with_status(obj, frame_list)


def unbreak_rotation_act(*, product: int) -> ActionStatus:
    settings = get_settings(product)
    geotracker = settings.get_current_geotracker_item()
    obj = geotracker.animatable_object()
    return unbreak_object_rotation_act(obj)


def mark_object_keyframes(obj: Object, *, product: int) -> None:
    settings = get_settings(product)
    gt = settings.loader().kt_geotracker()
    tracked_keyframes = gt.track_frames()
    _log.output(f'KEYFRAMES TO MARK AS TRACKED: {tracked_keyframes}')
    mark_selected_points_in_locrot(obj, tracked_keyframes, 'JITTER')
    keyframes = gt.keyframes()
    _log.output(f'KEYFRAMES TO MARK AS KEYFRAMES: {keyframes}')
    mark_selected_points_in_locrot(obj, keyframes, 'KEYFRAME')


def unbreak_after(frame_list: List, *,
                  product: int = ProductType.GEOTRACKER) -> None:
    _log.output(f'unbreak_after call {product_name(product)}')
    prefs = get_addon_preferences()
    if not prefs.gt_auto_unbreak_rotation:
        _log.output('unbreak rotation is switched off')
        return

    settings = get_settings(product)
    geotracker = settings.get_current_geotracker_item()
    obj = geotracker.animatable_object()
    unbreak_status = unbreak_rotation_with_status(obj, frame_list)
    if not unbreak_status.success:
        _log.error(unbreak_status.error_message)
    else:
        mark_object_keyframes(obj, product=product)


def unbreak_after_facetracker(frame_list: List) -> None:
    _log.output('unbreak_after_facetracker call')
    return unbreak_after(frame_list, product=ProductType.FACETRACKER)


def unbreak_after_reversed(frame_list: List, *,
                           product: int = ProductType.GEOTRACKER) -> None:
    _log.output('unbreak_after_reversed call')
    return unbreak_after(list(reversed(frame_list)), product=product)


def unbreak_after_reversed_facetracker(frame_list: List) -> None:
    _log.output('unbreak_after_reversed_facetracker call')
    return unbreak_after_reversed(frame_list, product=ProductType.FACETRACKER)
