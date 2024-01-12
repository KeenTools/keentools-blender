import numpy as np
from ..blender_independent_packages.pykeentools_loader import module as pkt_module


from ..addon_config import fb_settings


class FaceBuilderCameraInput(pkt_module().FaceBuilderCameraInputI):
    @classmethod
    def _camera_at(cls, keyframe):
        settings = fb_settings()
        head = settings.get_current_head()
        assert head is not None
        return head.get_camera_by_keyframe(keyframe)

    def projection(self, keyframe):
        camera = self._camera_at(keyframe)
        assert camera is not None
        return camera.get_projection_matrix()

    def view(self, keyframe):
        return np.eye(4)

    def image_size(self, keyframe):
        camera = self._camera_at(keyframe)
        assert camera is not None
        return camera.get_oriented_image_size()
