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

from typing import List

from error.tutorial_module import AssistanceParameterException
from model.core.tutorial_module import AssistanceParameter


def get_first_assistance_parameter_by_key(
        parameters: List[AssistanceParameter], parameter_key: str
) -> AssistanceParameter:
    for parameter in parameters:
        if parameter.key == parameter_key:
            return parameter
    raise AssistanceParameterException()


def get_assistance_parameters_by_key(
        parameters: List[AssistanceParameter], parameter_key: str
) -> List[AssistanceParameter]:
    assistance_parameters = []
    for parameter in parameters:
        if parameter.key == parameter_key:
            assistance_parameters.append(parameter)
    if len(assistance_parameters) == 0:
        raise AssistanceParameterException()
    return assistance_parameters


def get_assistance_parameters_by_keys(
        parameters: List[AssistanceParameter], parameter_keys: List[str]
) -> List[AssistanceParameter]:
    assistance_parameters = []
    for parameter in parameters:
        if parameter.key in parameter_keys:
            assistance_parameters.append(parameter)
    if len(assistance_parameters) == 0:
        raise AssistanceParameterException()
    return assistance_parameters


def replace_or_add_assistance_parameters_by_key(replacement: AssistanceParameter,
                                                parameters: List[AssistanceParameter] = None) -> List[
    AssistanceParameter]:
    if parameters is None:
        return []
    filtered_parameters = list(filter(lambda parameter: parameter.key != replacement.key, parameters))
    filtered_parameters.append(replacement)
    return filtered_parameters
