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

from model.core import GenericModel, parse_data_element
from model.core.dot_dict import DotDict


class Setting(GenericModel):
    def _init(self, data):
        def parse_function(d):
            # Dict?
            if type(d) is dict:
                return DotDict(d)
            # Str?
            if type(d) is str and (d.lower() in ("true", "t") or d.lower() in ("false", "f")):
                return d.lower() in ("true", "t")
            # Float?
            if type(d) is str and ("." in d or "," in d):
                try:
                    float_value = float(d)
                    return float_value
                except ValueError:
                    pass
            # Int?
            if type(d) is str:
                try:
                    int_value = int(d)
                    return int_value
                except ValueError:
                    pass
            # Something else
            return d

        self.key = data.get("key")
        self.value = parse_data_element(data=data, key="value", parse_function=parse_function)
