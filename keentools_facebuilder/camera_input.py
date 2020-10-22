import numpy as np
from pykeentools import FaceBuilderCameraInputI

from . import FBCameraItem
from .settings import get_main_settings, FBSceneSettings


class FaceBuilderCameraInput(FaceBuilderCameraInputI):
    @staticmethod
    def _camera_at(frame) -> FBCameraItem:
        settings: FBSceneSettings = get_main_settings()
        return settings.get_camera(settings.current_headnum, frame - 1)

    def projection(self, frame):
        return self._camera_at(frame).get_projection_matrix()

    def view(self, frame):
        return np.eye(4)

    def image_size(self, frame):
        return self._camera_at(frame).get_image_size()
