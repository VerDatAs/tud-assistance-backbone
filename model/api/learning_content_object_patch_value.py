"""
    Assistance Backbone for the assistance system developed as part of the VerDatAs project
    Copyright (C) 2022-2024 TU Dresden (Max Schaible, Sebastian Kucharski)

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

    TUD Assistance Backbone API

    Component for analyzing learning process data in the form of xAPI statements and providing feedback to learners' interactions and assistance and suggestions with regard to the user's learning state and the corresponding learning content.

    The version of the OpenAPI document: 1.0.0
    Generated by OpenAPI Generator (https://openapi-generator.tech)

    Do not edit the class manually.
"""  # noqa: E501

from __future__ import annotations

import json
import pprint
import re  # noqa: F401
from typing import Union, List, Optional, Dict

from pydantic import BaseModel, StrictBool, StrictFloat, StrictInt, ValidationError, \
    field_validator
from pydantic import StrictStr
from typing_extensions import Literal

from model.api.learning_content_object import LearningContentObject
from model.api.learning_content_object_patch_value_one_of_inner import LearningContentObjectPatchValueOneOfInner

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

LEARNINGCONTENTOBJECTPATCHVALUE_ONE_OF_SCHEMAS = ["LearningContentObject",
                                                  "List[LearningContentObjectPatchValueOneOfInner]", "bool", "float",
                                                  "int", "str"]


class LearningContentObjectPatchValue(BaseModel):
    """
    The value of the LCO attribute to set. This is required if the operation is `ADD` or `UPDATE`.
    """
    # data type: str
    oneof_schema_1_validator: Optional[StrictStr] = None
    # data type: float
    oneof_schema_2_validator: Optional[Union[StrictFloat, StrictInt]] = None
    # data type: int
    oneof_schema_3_validator: Optional[StrictInt] = None
    # data type: bool
    oneof_schema_4_validator: Optional[StrictBool] = None
    # data type: LearningContentObject
    oneof_schema_5_validator: Optional[LearningContentObject] = None
    # data type: List[LearningContentObjectPatchValueOneOfInner]
    oneof_schema_6_validator: Optional[List[LearningContentObjectPatchValueOneOfInner]] = None
    actual_instance: Optional[
        Union[LearningContentObject, List[LearningContentObjectPatchValueOneOfInner], bool, float, int, str]] = None
    one_of_schemas: List[str] = Literal[
        "LearningContentObject", "List[LearningContentObjectPatchValueOneOfInner]", "bool", "float", "int", "str"]

    model_config = {
        "validate_assignment": True,
        "protected_namespaces": (),
    }

    def __init__(self, *args, **kwargs) -> None:
        if args:
            if len(args) > 1:
                raise ValueError("If a position argument is used, only 1 is allowed to set `actual_instance`")
            if kwargs:
                raise ValueError("If a position argument is used, keyword arguments cannot be used.")
            super().__init__(actual_instance=args[0])
        else:
            super().__init__(**kwargs)

    @field_validator('actual_instance')
    def actual_instance_must_validate_oneof(cls, v):
        instance = LearningContentObjectPatchValue.model_construct()
        error_messages = []
        match = 0
        # validate data type: str
        try:
            instance.oneof_schema_1_validator = v
            match += 1
        except (ValidationError, ValueError) as e:
            error_messages.append(str(e))
        # validate data type: float
        try:
            instance.oneof_schema_2_validator = v
            match += 1
        except (ValidationError, ValueError) as e:
            error_messages.append(str(e))
        # validate data type: int
        try:
            instance.oneof_schema_3_validator = v
            match += 1
        except (ValidationError, ValueError) as e:
            error_messages.append(str(e))
        # validate data type: bool
        try:
            instance.oneof_schema_4_validator = v
            match += 1
        except (ValidationError, ValueError) as e:
            error_messages.append(str(e))
        # validate data type: LearningContentObject
        if not isinstance(v, LearningContentObject):
            error_messages.append(f"Error! Input type `{type(v)}` is not `LearningContentObject`")
        else:
            match += 1
        # validate data type: List[LearningContentObjectPatchValueOneOfInner]
        try:
            instance.oneof_schema_6_validator = v
            match += 1
        except (ValidationError, ValueError) as e:
            error_messages.append(str(e))
        if match > 1:
            # more than 1 match
            raise ValueError(
                "Multiple matches found when setting `actual_instance` in LearningContentObjectPatchValue with oneOf schemas: LearningContentObject, List[LearningContentObjectPatchValueOneOfInner], bool, float, int, str. Details: " + ", ".join(
                    error_messages))
        elif match == 0:
            # no match
            raise ValueError(
                "No match found when setting `actual_instance` in LearningContentObjectPatchValue with oneOf schemas: LearningContentObject, List[LearningContentObjectPatchValueOneOfInner], bool, float, int, str. Details: " + ", ".join(
                    error_messages))
        else:
            return v

    @classmethod
    def from_dict(cls, obj: dict) -> Self:
        return cls.from_json(json.dumps(obj))

    @classmethod
    def from_json(cls, json_str: str) -> Self:
        """Returns the object represented by the json string"""
        instance = cls.model_construct()
        error_messages = []
        match = 0

        # deserialize data into str
        try:
            # validation
            instance.oneof_schema_1_validator = json.loads(json_str)
            # assign value to actual_instance
            instance.actual_instance = instance.oneof_schema_1_validator
            match += 1
        except (ValidationError, ValueError) as e:
            error_messages.append(str(e))
        # deserialize data into float
        try:
            # validation
            instance.oneof_schema_2_validator = json.loads(json_str)
            # assign value to actual_instance
            instance.actual_instance = instance.oneof_schema_2_validator
            match += 1
        except (ValidationError, ValueError) as e:
            error_messages.append(str(e))
        # deserialize data into int
        try:
            # validation
            instance.oneof_schema_3_validator = json.loads(json_str)
            # assign value to actual_instance
            instance.actual_instance = instance.oneof_schema_3_validator
            match += 1
        except (ValidationError, ValueError) as e:
            error_messages.append(str(e))
        # deserialize data into bool
        try:
            # validation
            instance.oneof_schema_4_validator = json.loads(json_str)
            # assign value to actual_instance
            instance.actual_instance = instance.oneof_schema_4_validator
            match += 1
        except (ValidationError, ValueError) as e:
            error_messages.append(str(e))
        # deserialize data into LearningContentObject
        try:
            instance.actual_instance = LearningContentObject.from_json(json_str)
            match += 1
        except (ValidationError, ValueError) as e:
            error_messages.append(str(e))
        # deserialize data into List[LearningContentObjectPatchValueOneOfInner]
        try:
            # validation
            instance.oneof_schema_6_validator = json.loads(json_str)
            # assign value to actual_instance
            instance.actual_instance = instance.oneof_schema_6_validator
            match += 1
        except (ValidationError, ValueError) as e:
            error_messages.append(str(e))

        if match > 1:
            # more than 1 match
            raise ValueError(
                "Multiple matches found when deserializing the JSON string into LearningContentObjectPatchValue with oneOf schemas: LearningContentObject, List[LearningContentObjectPatchValueOneOfInner], bool, float, int, str. Details: " + ", ".join(
                    error_messages))
        elif match == 0:
            # no match
            raise ValueError(
                "No match found when deserializing the JSON string into LearningContentObjectPatchValue with oneOf schemas: LearningContentObject, List[LearningContentObjectPatchValueOneOfInner], bool, float, int, str. Details: " + ", ".join(
                    error_messages))
        else:
            return instance

    def to_json(self) -> str:
        """Returns the JSON representation of the actual instance"""
        if self.actual_instance is None:
            return "null"

        to_json = getattr(self.actual_instance, "to_json", None)
        if callable(to_json):
            return self.actual_instance.to_json()
        else:
            return json.dumps(self.actual_instance)

    def to_dict(self) -> Dict:
        """Returns the dict representation of the actual instance"""
        if self.actual_instance is None:
            return None

        to_dict = getattr(self.actual_instance, "to_dict", None)
        if callable(to_dict):
            return self.actual_instance.to_dict()
        else:
            # primitive type
            return self.actual_instance

    def to_str(self) -> str:
        """Returns the string representation of the actual instance"""
        return pprint.pformat(self.model_dump())
