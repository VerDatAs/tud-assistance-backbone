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
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import BaseModel, Field, StrictStr

from model.api.learning_content_object_attribute import LearningContentObjectAttribute

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self


class LearningContentObject(BaseModel):
    """
    Schema for representing a generic Learning Content Object (LCO).
    """  # noqa: E501
    lco_id: StrictStr = Field(description="The unique ID of this LCO.", alias="lcoId")
    lco_type: StrictStr = Field(description="The unique identifier of the type of the LCO.", alias="lcoType")
    object_id: Optional[StrictStr] = Field(default=None,
                                           description="The ID which is used to identify the LCO in an xAPI-statement.",
                                           alias="objectId")
    attributes: Optional[List[LearningContentObjectAttribute]] = Field(default=None,
                                                                       description="A list of attributes of the LCO.")
    __properties: ClassVar[List[str]] = ["lcoId", "lcoType", "objectId", "attributes"]

    model_config = {
        "populate_by_name": True,
        "validate_assignment": True,
        "protected_namespaces": (),
    }

    def __init__(__pydantic_self__, **data: Any) -> None:
        super().__init__(**data)
        if __pydantic_self__.attributes is None or len(__pydantic_self__.attributes) == 0:
            return
        for i, attribute in enumerate(__pydantic_self__.attributes):
            if type(attribute.value) is dict:
                __pydantic_self__.attributes[i].value = LearningContentObject.model_validate(attribute.value)
            elif type(attribute.value) is list:
                __pydantic_self__.attributes[i].value = list(
                    map(lambda sub_preliminary_lco: LearningContentObject.model_validate(
                        sub_preliminary_lco),
                        attribute.value))

    def to_str(self) -> str:
        """Returns the string representation of the model using alias"""
        return pprint.pformat(self.model_dump(by_alias=True))

    def to_json(self) -> str:
        """Returns the JSON representation of the model using alias"""
        # TODO: pydantic v2: use .model_dump_json(by_alias=True, exclude_unset=True) instead
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> Self:
        """Create an instance of LearningContentObject from a JSON string"""
        return cls.from_dict(json.loads(json_str))

    def to_dict(self) -> Dict[str, Any]:
        """Return the dictionary representation of the model using alias.

        This has the following differences from calling pydantic's
        `self.model_dump(by_alias=True)`:

        * `None` is only added to the output dict for nullable fields that
          were set at model initialization. Other fields with value `None`
          are ignored.
        """
        _dict = self.model_dump(
            by_alias=True,
            exclude={
            },
            exclude_none=True,
        )
        # override the default output from pydantic by calling `to_dict()` of each item in attributes (list)
        _items = []
        if self.attributes:
            for _item in self.attributes:
                if _item:
                    _items.append(_item.to_dict())
            _dict['attributes'] = _items
        return _dict

    @classmethod
    def from_dict(cls, obj: Dict) -> Self:
        """Create an instance of LearningContentObject from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate({
            "lcoId": obj.get("lcoId"),
            "lcoType": obj.get("lcoType"),
            "objectId": obj.get("objectId"),
            "attributes": [LearningContentObjectAttribute.from_dict(_item) for _item in
                           obj.get("attributes")] if obj.get("attributes") is not None else None
        })
        return _obj
