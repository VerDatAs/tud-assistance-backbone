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
from service.db import get_mongo_db_client, SETTINGS_COLLECTION_NAME


def read_setting_by_key(setting_key: str) -> Setting | None:
    find_one_result = get_mongo_db_client()[SETTINGS_COLLECTION_NAME].find_one(
        {"key": setting_key}
    )
    return None if find_one_result is None else Setting(find_one_result)


def update_setting_by_key(key: str, setting: Setting) -> None:
    get_mongo_db_client()[SETTINGS_COLLECTION_NAME].replace_one(
        {"key": key},
        setting.to_dict(),
        upsert=True
    )
