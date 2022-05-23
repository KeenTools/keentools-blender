# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2022 KeenTools

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# ##### END GPL LICENSE BLOCK #####

import numpy as np
import logging

import bpy

from ..geotracker_config import get_gt_settings
from ..utils import coords
from ..utils.animation import get_safe_evaluated_fcurve
from ..blender_independent_packages.pykeentools_loader import module as pkt_module


class GTCameraInput(pkt_module().TrackerCameraInputI):
    def projection(self, frame):
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return np.eye(4)
        camera = geotracker.camobj
        assert camera is not None
        cam_data = camera.data
        near = 0.1
        far = 1000.0
        scene = bpy.context.scene
        w = scene.render.resolution_x
        h = scene.render.resolution_y
        lens = get_safe_evaluated_fcurve(cam_data, frame, 'lens')
        proj_mat = coords.projection_matrix(w, h, lens,
                                            cam_data.sensor_width,
                                            near, far, scale=1.0)
        return proj_mat

    def view(self, keyframe):
        return np.eye(4)

    def image_size(self):
        scene = bpy.context.scene
        w = scene.render.resolution_x
        h = scene.render.resolution_y
        return (w, h)


class GTGeoInput(pkt_module().GeoInputI):
    def geo_hash(self):
        return pkt_module().Hash(42)

    def geo(self):
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return None
        return self.init_geo(coords.evaluated_mesh(geotracker.geomobj))

    @staticmethod
    def init_geo(obj):
        mesh = obj.data
        scale = coords.get_scale_matrix_3x3_from_matrix_world(obj.matrix_world)
        verts = coords.get_mesh_verts(obj) @ scale

        mb = pkt_module().MeshBuilder()
        mb.add_points(verts @ coords.xz_to_xy_rotation_matrix_3x3())

        for polygon in mesh.polygons:
            mb.add_face(polygon.vertices[:])

        _geo = pkt_module().Geo()
        _geo.add_mesh(mb.mesh())
        return _geo


class GTImageInput(pkt_module().ImageInputI):
    def image_hash(self, frame):
        return pkt_module().Hash(frame)

    def load_linear_rgb_image_at(self, frame):
        logger = logging.getLogger(__name__)
        logger.debug('load_linear_rgb_image_at: {}'.format(frame))
        settings = get_gt_settings()
        frame_filepath = settings.get_frame_image_path(frame)
        logger.debug('frame_filepath: {}'.format(frame_filepath))

        img = bpy.data.images.load(frame_filepath)
        size = img.size
        logger.debug('img.size: {} {}'.format(size[0], size[1]))

        np_img0 = np.asarray(img.pixels[:], dtype=np.float32)
        np_img = np_img0.reshape((size[1], size[0], 4))
        bpy.data.images.remove(img, do_unlink=True)
        return np_img[:, :, :3]

    def first_frame(self):
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return 1
        return geotracker.precalc_start

    def last_frame(self):
        settings = get_gt_settings()
        geotracker = settings.get_current_geotracker_item()
        if not geotracker:
            return 0
        return geotracker.precalc_end


class GTMask2DInput(pkt_module().Mask2DInputI):
    def load_2d_mask_at(self, frame):
        return None
