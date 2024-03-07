"""
    Assistance Backbone for the assistance system developed as part of the VerDatAs project
    Copyright (C) 2022-2024 TU Dresden (Robert Schmidt)

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

"""
    Ollama API

    API Spec for Ollama API. Please see https://github.com/jmorganca/ollama/blob/main/docs/api.md for more details.

    The version of the OpenAPI document: 0.1.9
    Generated by OpenAPI Generator (https://openapi-generator.tech)

    Do not edit the class manually.
"""  # noqa: E501

from __future__ import annotations

import json
import re  # noqa: F401
from enum import Enum

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self


class ResponseFormat(str, Enum):
    """
    The format to return a response in. Currently the only accepted value is json.  Enable JSON mode by setting the format parameter to json. This will structure the response as valid JSON.  Note: it's important to instruct the model to use JSON in the prompt. Otherwise, the model may generate large amounts whitespace. 
    """

    """
    allowed enum values
    """
    JSON = 'json'

    @classmethod
    def from_json(cls, json_str: str) -> Self:
        """Create an instance of ResponseFormat from a JSON string"""
        return cls(json.loads(json_str))
