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

from typing import List, Any

from model.core.expert_module import LearningContentObject
from service.db.learning_content_object import read_learning_content_object_by_lco_id


def get_learning_content_object_attribute_value(lco: LearningContentObject, lco_attribute_key: str) -> Any | None:
    if lco.attributes is None or len(lco.attributes) == 0:
        return None
    for lco_attribute in lco.attributes:
        if lco_attribute.key == lco_attribute_key:
            return lco_attribute.value
    return None


def get_root_lco(lco: LearningContentObject) -> LearningContentObject:
    work_lco = lco
    while work_lco.parent_lco_id is not None:
        work_lco = read_learning_content_object_by_lco_id(work_lco.parent_lco_id)
    return work_lco


def get_sub_learning_content_objects(lco: LearningContentObject) -> List[LearningContentObject]:
    if lco is None or lco.attributes is None or (not lco.attributes):
        return []

    sub_lco_list = []
    for attribute in lco.attributes:
        if type(attribute.value) is LearningContentObject:
            sub_lco_list.append(attribute.value)
            sub_lco_list += get_sub_learning_content_objects(attribute.value)
        elif type(attribute.value) is list:
            for value_element in attribute.value:
                if type(value_element) is LearningContentObject:
                    sub_lco_list.append(value_element)
                    sub_lco_list += get_sub_learning_content_objects(value_element)

    return sub_lco_list


def get_sub_learning_content_object_object_ids(lco: LearningContentObject) -> List[str]:
    sub_lcos = get_sub_learning_content_objects(lco)
    return [sub_lco.object_id for sub_lco in sub_lcos]
