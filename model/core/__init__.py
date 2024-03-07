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

from abc import abstractmethod
from copy import deepcopy
from datetime import datetime
from enum import Enum
from typing import Callable, Any

from model.core.dot_dict import DotDict
from service.datetime import datetime_to_string


def parse_data_element(data: dict, key: str,
                       parse_function: Callable = lambda list_element: DotDict(list_element),
                       default_value: Any = None) -> Any:
    return (
        default_value
        if data.get(key) is None
        else parse_function(data.get(key)))


def parse_data_list_element(data: dict, key: str,
                            parse_function: Callable = lambda list_element: DotDict(list_element),
                            default_value: Any = []) -> Any:
    return (
        default_value
        if data.get(key) is None
        else list(map(parse_function, data.get(key))))


def parse_data_bool_element(data: dict, key: str, default_value: bool | None = None) -> bool | None:
    return default_value if data.get(key) is None else data.get(key) if type(data.get(key)) is bool else data.get(
        key).lower() in ("true", "t", "1")


class GenericModel:
    datetime_to_string = True

    @abstractmethod
    def _init(self, data):
        raise NotImplementedError()

    def to_dict(self) -> dict:
        def process_dict_value(dict_value: Any) -> Any:
            if hasattr(dict_value, 'to_dict'):
                return dict_value.to_dict()
            elif type(dict_value) is datetime:
                return datetime_to_string(dict_value) if self.datetime_to_string else dict_value
            elif type(dict_value) is list:
                return list(
                    map(lambda dict_value_list_element: process_dict_value(dict_value_list_element), dict_value))
            elif isinstance(dict_value, Enum):
                return dict_value.value
            else:
                return dict_value

        dict_representation = deepcopy(self).__dict__
        keys_with_none_values = []
        for key, value in dict_representation.items():
            if value is None:
                keys_with_none_values.append(key)
            else:
                dict_representation[key] = process_dict_value(value)
        for key in keys_with_none_values:
            dict_representation.pop(key)
        return process_dict_value(dict_representation)

    def __init__(self, data=None) -> None:
        super().__init__()
        data = {} if data is None else data
        self._init(data)
        for attribute_key in data.keys():
            try:
                self.__getattribute__(attribute_key)
            except AttributeError:
                attribute_value = data.get(attribute_key)
                if type(attribute_value) is dict:
                    self.__setattr__(attribute_key, DotDict(data.get(attribute_key)))
                else:
                    self.__setattr__(attribute_key, data.get(attribute_key))

    def as_dot_map(self):
        return DotDict(self.to_dict())


class ModelList:
    def __init__(
            self,
            model_list,
            model_list_name: str,
            total_number_of_models: int,
            provided_number_of_models: int,
            page_number: int = None,
    ):
        self.model_list_name = model_list_name
        self.__setattr__(model_list_name, model_list)
        self.total_number = total_number_of_models
        self.provided_number = provided_number_of_models
        self.page_number = 1 if page_number is None else page_number

    def to_dict(self):
        copy = deepcopy(self)
        if not (not self.__getattribute__(self.model_list_name)):
            copy.__setattr__(
                self.model_list_name,
                list(
                    map(
                        lambda model: model.to_dict(),
                        self.__getattribute__(self.model_list_name),
                    )
                ),
            )
        dict_object = copy.__dict__
        dict_object.pop("model_list_name")
        return dict_object
