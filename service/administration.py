"""
    Assistance Backbone for the assistance system developed as part of the VerDatAs project
    Copyright (C) 2022-2024 TU Dresden (Sebastian Kucharski)

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from model.core.administration import Setting
from service.db.setting import read_setting_by_key as read_setting_from_db_by_key
from service.db.setting import update_setting_by_key as update_setting_from_db_by_key
from service.environment import debug as debug_enabled_by_env_var

SETTING_KEY_DEBUG = "debug"
SETTING_KEY_DEBUG_SCHEDULED_ASSISTANCE_TIME_FACTOR = "debug_scheduled_assistance_time_factor"
SETTING_KEY_SCHEDULED_ASSISTANCE_DISABLED = "scheduled_assistance_disabled"


def debug() -> bool:
    if debug_enabled_by_env_var():
        return True
    debug_setting = read_setting_by_key(SETTING_KEY_DEBUG)
    if debug_setting is not None and debug_setting.value:
        return True

    return False


def read_setting_by_key(setting_key: str) -> Setting | None:
    return read_setting_from_db_by_key(setting_key)


def update_setting_by_key(key: str, setting: Setting) -> None:
    return update_setting_from_db_by_key(key, setting)
