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

from enum import Enum

from model.core import GenericModel, parse_data_list_element, parse_data_element

LCO_ATTRIBUTE_KEY_ENTRY_TEST_INDICATOR = "isEntryTest"
LCO_ATTRIBUTE_KEY_FINAL_TEST_INDICATOR = "isFinalTest"


class LearningContentObject(GenericModel):
    def _init(self, data):
        self.lco_id = data.get("lco_id")
        self.parent_lco_id = data.get("parent_lco_id")
        self.lco_type = data.get("lco_type")
        self.object_id = data.get("object_id")
        self.updated = data.get("updated")
        self.attributes = parse_data_list_element(data=data, key="attributes",
                                                  parse_function=lambda d: LearningContentObjectAttribute(d))


class LearningContentObjectAttribute(GenericModel):
    def _init(self, data):
        self.key = data.get("key")
        self.value = parse_data_list_element(data=data, key="value",
                                             parse_function=lambda d: LearningContentObject(d) if type(
                                                 d) is dict else d) if type(
            data.get("value")) is list else parse_data_element(data=data, key="value",
                                                               parse_function=lambda d: LearningContentObject(
                                                                   d) if type(d) is dict else d)


class LearningContentObjectAttributeModel(GenericModel):
    def _init(self, data):
        self.key = data.get("key")
        self.type = data.get("type")
        self.required = data.get("required")
        self.allowed_values = parse_data_list_element(data=data, key="allowed_values",
                                                      parse_function=lambda d: LearningContentObject(d) if type(
                                                          d) is dict else d, default_value=None)


class LearningContentObjectModel(GenericModel):
    def _init(self, data):
        self.lco_type = data.get("lco_type")
        self.attributes = parse_data_list_element(data=data, key="attributes",
                                                  parse_function=lambda d: LearningContentObjectAttributeModel(d))


class LearningContentObjectParameterSearchCriteria(GenericModel):
    def _init(self, data):
        self.key = data.get("key")
        self.value = data.get("value")


class LearningContentObjectPatchOperation(Enum):
    ADD = "ADD"
    DELETE = "DELETE"
    UPDATE = "UPDATE"
