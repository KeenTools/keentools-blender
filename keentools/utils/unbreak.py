from typing import Any, List

from bpy.types import Object

from .kt_logging import KTLogger
from ..addon_config import ActionStatus, ProductType, get_settings
from .animation import (get_action,
                        get_object_keyframe_numbers,
                        mark_selected_points_in_locrot)
from ..geotracker.utils.tracking import (unbreak_rotation,
                                         check_unbreak_rotaion_is_needed)


_log = KTLogger(__name__)


def unbreak_rotation_act(
        *, product: int = ProductType.GEOTRACKER) -> ActionStatus:
    settings = get_settings(product)
    geotracker = settings.get_current_geotracker_item()
    obj = geotracker.animatable_object()
    return unbreak_object_rotation_act(obj)


def unbreak_object_rotation_act(obj: Object) -> ActionStatus:
    if not obj:
        return ActionStatus(False, 'No object to unbreak rotation')
    frame_list = get_object_keyframe_numbers(obj, loc=False, rot=True)
    return unbreak_rotation_with_status(obj, frame_list)


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

    if unbreak_rotation(obj, frame_list):
        _mark_object_keyframes(obj)
    return ActionStatus(True, 'ok')


def _mark_object_keyframes(obj: Object, *,
                           product: int = ProductType.GEOTRACKER) -> None:
    settings = get_settings(product)
    gt = settings.loader().kt_geotracker()
    tracked_keyframes = [x for x in gt.track_frames()]
    _log.output(f'KEYFRAMES TO MARK AS TRACKED: {tracked_keyframes}')
    mark_selected_points_in_locrot(obj, tracked_keyframes, 'JITTER')
    keyframes = [x for x in gt.keyframes()]
    _log.output(f'KEYFRAMES TO MARK AS KEYFRAMES: {keyframes}')
    mark_selected_points_in_locrot(obj, keyframes, 'KEYFRAME')
