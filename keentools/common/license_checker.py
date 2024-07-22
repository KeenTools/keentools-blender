# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2022  KeenTools

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

from typing import Optional, Any

from ..utils.kt_logging import KTLogger
from ..utils.version import BVersion
from ..addon_config import (Config,
                            get_operator,
                            ErrorType,
                            ProductType,
                            product_name)
from ..preferences.operators import get_product_license_manager
from ..blender_independent_packages.pykeentools_loader \
    import is_installed as pkt_is_installed, module as pkt_module


_log = KTLogger(__name__)


class KTLicenseStatus:
    def __init__(self, product: int):
        self.product: int = product
        self.response: Any = None
        self.attempts: int = 0
        self.trial_licensed: bool = False
        self.float_licensed: bool = False
        self.subscription_licensed: bool = False
        self.licensed: bool = False
        self.checked: bool = False
        self.days_left: int = 0
        self.license_type: str = 'undefined'
        self.show_message: bool = False

    def parse_response(self) -> bool:
        _log.yellow('parse_response start')
        self.attempts += 1
        if not self.response:
            return False

        successfull_set = {'succeed'}
        try:
            self.trial_licensed = self.response.trial_status.status in successfull_set
            self.float_licensed = self.response.floating_status.status in successfull_set
            self.subscription_licensed = self.response.subscription_license_used
            self.licensed = self.response.license_status.status in successfull_set
            self.days_left = self.response.days_left
        except Exception as err:
            _log.error(f'{self.__class__.__name__} Exception:\n{str(err)}')
            return False

        self.checked = True
        if self.float_licensed:
            self.license_type = 'floating'
        elif self.subscription_licensed and self.licensed:
            self.license_type = 'subscription'
        elif self.licensed:
            self.license_type = 'regular'
        elif self.trial_licensed:
            self.license_type = 'trial'
            self.show_message = True
        else:
            self.license_type = 'expired trial'
            self.show_message = True

        _log.output('parse_response end >>>')
        return True


def _output_check_result(res) -> None:
    _log.red(f'Check result:\n----'
             f'\ndays_left: {res.days_left}'
             f'\nfloating_license_installed: {res.floating_license_installed}'
             f'\nfloating_status: {res.floating_status}'
             f'\nmessage: #{res.floating_status.message}#'
             f'\nstatus: #{res.floating_status.status}#'
             f'\nlicense_status: {res.license_status}'
             f'\nmessage: #{res.license_status.message}#'
             f'\nstatus: #{res.license_status.status}#'
             f'\nstate: {res.state}'
             f'\nsubscription_license_used: {res.subscription_license_used}'
             f'\ntrial_status: {res.trial_status}'
             f'\nmessage: #{res.trial_status.message}#'
             f'\nstatus: #{res.trial_status.status}#'
             f'\n----')


fb_license_status: Any = KTLicenseStatus(ProductType.FACEBUILDER)
gt_license_status: Any = KTLicenseStatus(ProductType.GEOTRACKER)
ft_license_status: Any = KTLicenseStatus(ProductType.FACETRACKER)


def get_product_license_status(product: int) -> Any:
    if product == ProductType.FACEBUILDER:
        return fb_license_status
    elif product == ProductType.GEOTRACKER:
        return gt_license_status
    elif product == ProductType.FACETRACKER:
        return ft_license_status
    assert False, 'Unknown product type in check_license'


def _upgrade_url(plugin_name: str,
                 plugin_version: str,
                 days_left: int = -1,
                 os_name: str = BVersion.os_name,
                 plugin_host: str = 'blender',
                 current_license: str = 'trial') -> str:
    url_txt = (f'https://keentools.io/buy-from-plugin?os={os_name}'
               f'&plugin_host={plugin_host}'
               f'&plugin_name={plugin_name}'
               f'&plugin_version={plugin_version}'
               f'&days_left={days_left}'
               f'&current_license={current_license}')
    return url_txt


def _fb_upgrade_url() -> str:
    license_status = get_product_license_status(ProductType.FACEBUILDER)
    return _upgrade_url(plugin_name='facebuilder',
                        plugin_version=f'{Config.addon_version}',
                        days_left=license_status.days_left)


def _gt_upgrade_url() -> str:
    license_status = get_product_license_status(ProductType.GEOTRACKER)
    return _upgrade_url(plugin_name='geotracker',
                        plugin_version=f'{Config.addon_version}',
                        days_left=license_status.days_left)


def _ft_upgrade_url() -> str:
    license_status = get_product_license_status(ProductType.GEOTRACKER)
    return _upgrade_url(plugin_name='facetracker',
                        plugin_version=f'{Config.addon_version}',
                        days_left=license_status.days_left)


def get_upgrade_url(product: int) -> str:
    if product == ProductType.FACEBUILDER:
        url = _fb_upgrade_url()
    elif product == ProductType.GEOTRACKER:
        url = _gt_upgrade_url()
    elif product == ProductType.FACETRACKER:
        url = _ft_upgrade_url()
    else:
        assert False, 'Wrong product in get_upgrade_url'
    return url


def check_license(product: int) -> Optional[float]:
    _log.output(f'LICENSE CHECK FOR {product_name(product)}')
    if not pkt_is_installed():
        _log.info(f'Core is not installed. '
                  f'Wait for {Config.kt_license_recheck_timeout} sec.')
        return Config.kt_license_recheck_timeout

    try:
        lm = get_product_license_manager(product=product)
        check_result_tupple = lm.perform_license_and_trial_check(
            strategy=pkt_module().LicenseCheckStrategy.FORCE)
        res = check_result_tupple[0]
        _output_check_result(res)

        license_status = get_product_license_status(product)
        license_status.response = res
        if not license_status.parse_response():
            return Config.kt_license_recheck_timeout
        license_status.checked = True
    except Exception as err:
        _log.error(f'check_license Exception:\n{str(err)}')
        return Config.kt_license_recheck_timeout

    _log.output('LICENSE CHECK end >>>')
    return None


def draw_upgrade_license_box(layout, product):
    if not fb_license_status.checked and not fb_license_status.show_message:
        return

    license_status = get_product_license_status(product)
    box = layout.box()
    main_col = box.column(align=True)
    split = main_col.split(factor=0.1, align=True)
    col = split.column(align=True)
    col.alert = True
    col.label(text='', icon='ERROR')
    if license_status.license_type == 'trial':
        col = split.column(align=True)
        col.alert = license_status.days_left <= Config.license_minimum_days_for_warning
        col.label(text=f'{license_status.days_left} days of free trial remaining')
    else:
        col = split.column(align=True)
        col.alert = True
        col.scale_y = Config.text_scale_y
        col.label(text='Your free trial is over')
    op = main_col.operator(Config.kt_upgrade_product_idname, icon='WORLD')
    op.product = product
