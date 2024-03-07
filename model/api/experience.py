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

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self


class Experience(BaseModel):
    """
    Schema for representing an experience collected for a learner.
    """  # noqa: E501
    timestamp: StrictStr = Field(description="The timestamp of the experience.")
    statement_id: Optional[StrictStr] = Field(default=None,
                                              description="The ID of the statement to which the experience relates.",
                                              alias="statementId")
    object_id: Optional[StrictStr] = Field(default=None,
                                           description="The ID of the object which is referenced in the related statement.",
                                           alias="objectId")
    lco_id: Optional[StrictStr] = Field(default=None, description="The unique ID of this LCO.", alias="lcoId")
    verb_id: Optional[StrictStr] = Field(default=None,
                                         description="The ID of the verb which is referenced in the related statement.",
                                         alias="verbId")
    result: Optional[Any] = Field(default=None,
                                  description="The result of the experience, if any, as reported in the statement.")
    __properties: ClassVar[List[str]] = ["timestamp", "statementId", "objectId", "lcoId", "verbId", "result"]

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
        """Create an instance of Experience from a JSON string"""
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
        return _dict

    @classmethod
    def from_dict(cls, obj: Dict) -> Self:
        """Create an instance of Experience from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate({
            "timestamp": obj.get("timestamp"),
            "statementId": obj.get("statementId"),
            "objectId": obj.get("objectId"),
            "lcoId": obj.get("lcoId"),
            "verbId": obj.get("verbId"),
            "result": obj.get("result")
        })
        return _obj
