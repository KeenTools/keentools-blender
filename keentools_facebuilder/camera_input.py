import keentools_facebuilder.blender_independent_packages.pykeentools_loader as pkt
import numpy as np

from .config import get_main_settings


class FaceBuilderCameraInput(pkt.module().FaceBuilderCameraInputI):
    @staticmethod
    def _camera_at(frame):
        settings = get_main_settings()
        head = settings.get_current_head()
        return head.get_camera_by_keyframe(frame)

    def projection(self, frame):
        return self._camera_at(frame).get_projection_matrix()

    def view(self, frame):
        return np.eye(4)

    def image_size(self, frame):
        return self._camera_at(frame).get_oriented_image_size()
