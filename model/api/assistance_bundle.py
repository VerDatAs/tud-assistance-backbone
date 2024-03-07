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
from typing import Any, ClassVar, Dict, List

from pydantic import BaseModel, Field

from model.api.assistance import Assistance

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self


class AssistanceBundle(BaseModel):
    """
    Schema for representing a bundle of provided assistance that might have different types.
    """  # noqa: E501
    assistance: List[Assistance] = Field(description="A list of provided assistance.")
    __properties: ClassVar[List[str]] = ["assistance"]

    model_config = {
        "populate_by_name": True,
        "validate_assignment": True,
        "protected_namespaces": (),
    }

    def to_str(self) -> str:
        """Returns the string representation of the model using alias"""
        return pprint.pformat(self.model_dump(by_alias=True))

    def to_json(self) -> str:
        """Returns the JSON representation of the model using alias"""
        # TODO: pydantic v2: use .model_dump_json(by_alias=True, exclude_unset=True) instead
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> Self:
        """Create an instance of AssistanceBundle from a JSON string"""
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
        # override the default output from pydantic by calling `to_dict()` of each item in assistance (list)
        _items = []
        if self.assistance:
            for _item in self.assistance:
                if _item:
                    _items.append(_item.to_dict())
            _dict['assistance'] = _items
        return _dict

    @classmethod
    def from_dict(cls, obj: Dict) -> Self:
        """Create an instance of AssistanceBundle from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate({
            "assistance": [Assistance.from_dict(_item) for _item in obj.get("assistance")] if obj.get(
                "assistance") is not None else None
        })
        return _obj
