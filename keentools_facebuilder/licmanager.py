# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019  KeenTools

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


import bpy
from . fbloader import FBLoader


class FBLicManager:
    fb = FBLoader.get_builder()
    lm = fb.license_manager()

    @classmethod
    def get_lm(cls):
        return cls.lm

    @staticmethod
    def get_prefs():
        return bpy.context.preferences.addons[__package__].preferences

    @classmethod
    def update_lic_status(cls):
        prefs = cls.get_prefs()
        lm = cls.get_lm()
        status = lm.license_status_text(force_check=False)
        prefs.lic_status = status
        # print(status)

    @classmethod
    def update_hardware_id(cls):
        prefs = cls.get_prefs()
        lm = cls.get_lm()
        prefs.hardware_id = lm.hardware_id()

    @classmethod
    def copy_hardware_id(cls):
        prefs = cls.get_prefs()
        lm = cls.get_lm()
        prefs.hardware_id = lm.hardware_id()
        bpy.context.window_manager.clipboard = prefs.hardware_id
        prefs.lic_offline_status = 'Hardware ID is in clipboard!'

    @classmethod
    def update_floating_params(cls):
        prefs = cls.get_prefs()
        lm = cls.get_lm()
        env = lm.env_server_info()
        if env is not None:
            prefs.license_server = env[0]
            prefs.license_server_port = env[1]
            prefs.license_server_lock = True
        else:
            # No Env vars
            prefs.license_server_lock = False

    @classmethod
    def connect_floating_lic(cls):
        prefs = cls.get_prefs()
        lm = cls.get_lm()
        res = lm.install_floating_license(
            prefs.license_server, prefs.license_server_port)
        if res is not None:
            prefs.lic_floating_status = res
        else:
            prefs.lic_floating_status = 'License is not found'

    @classmethod
    def install_online_lic(cls):
        lm = cls.get_lm()
        prefs = cls.get_prefs()
        res = lm.install_license_online(prefs.license_id)

        if res is not None:
            prefs.lic_online_status = res
        else:
            prefs.lic_online_status = "Online License ERROR"

    @classmethod
    def install_offline_lic(cls):
        lm = cls.get_lm()
        prefs = cls.get_prefs()
        res = lm.install_license_offline(prefs.lic_path)
        print(res)

        if res is not None:
            prefs.lic_offline_status = res
        else:
            prefs.lic_offline_status = "Offline License ERROR"
