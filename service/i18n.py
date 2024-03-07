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

from functools import lru_cache
from typing import List

from pyi18n import PyI18n

from service.environment import internationalization_files_path

LOCALE_IDENTIFIER_DE = "de"
LOCALE_IDENTIFIER_EN = "en"


def get_supported_locales() -> List[str]:
    return [LOCALE_IDENTIFIER_DE, LOCALE_IDENTIFIER_EN]


@lru_cache
def get_translator() -> PyI18n:
    return PyI18n(tuple(supported_locale for supported_locale in get_supported_locales()),
                  load_path=internationalization_files_path())


def t(locale: str, path: str, **kwargs) -> str:
    translator = get_translator()
    return translator.gettext(locale, path, **kwargs)
