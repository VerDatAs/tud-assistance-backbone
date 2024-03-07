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

from __future__ import annotations

from copy import deepcopy
from enum import Enum
from typing import List, Any

from error.tutorial_module import AssistanceParameterException
from model.core import GenericModel, parse_data_list_element, parse_data_element, parse_data_bool_element
from model.core.dot_dict import DotDict


def parse_assistance_parameters(data) -> List[AssistanceParameter]:
    return parse_data_list_element(data=data, key="parameters", parse_function=lambda d: AssistanceParameter(d))


class Assistance(GenericModel):
    @staticmethod
    def create_with_default_parameters(
            user_id: str,
            assistance_objects: List[AssistanceObject],
            next_operation_keys: List[str] = None,
    ) -> Assistance:
        assistance = Assistance()
        assistance.user_id = user_id
        assistance.assistance_objects = assistance_objects
        assistance.next_operation_keys = (
            [] if next_operation_keys is None else next_operation_keys
        )
        return assistance

    def _init(self, data):
        self.a_id = data.get("a_id")
        self.user_id = data.get("user_id")
        self.type_key = data.get("type_key")
        self.timestamp = data.get("timestamp")
        self.assistance_state = parse_data_element(data=data, key="assistance_state",
                                                   parse_function=lambda d: AssistanceState(d))
        self.parameters = parse_assistance_parameters(data)
        self.assistance_objects = parse_data_list_element(data=data, key="assistance_objects",
                                                          parse_function=lambda d: AssistanceObject(d))
        self.next_operation_keys = parse_data_list_element(data=data, key="next_operation_keys",
                                                           parse_function=lambda d: d)


class AssistanceContext:
    context_can_be_persisted = True

    def __init__(self, parameter_dict=None):
        if parameter_dict is None:
            parameter_dict = {}
        self.parameter_dict = parameter_dict

    def get_parameter(self, parameter_key: str, parameter_required: bool = True) -> any:
        if parameter_key not in self.parameter_dict:
            if not parameter_required:
                return None
            raise AssistanceParameterException(
                f"Required parameter '{parameter_key}' missing!"
            )
        return self.parameter_dict[parameter_key]

    def add_parameter(self, parameter_key: str, parameter_value: any) -> None:
        if parameter_key in self.parameter_dict:
            raise AssistanceParameterException(
                f"Parameter '{parameter_key}' already added!"
            )
        if parameter_value.__class__.__module__ == "__builtin__":
            self.context_can_be_persisted = False
        self.parameter_dict[parameter_key] = parameter_value


class AssistanceObject(GenericModel):
    @staticmethod
    def create_with_default_parameters(
            user_id: str, parameters: List
    ) -> AssistanceObject:
        assistance_object = AssistanceObject()
        assistance_object.user_id = user_id
        assistance_object.parameters = parameters
        return assistance_object

    @staticmethod
    def create_with_parameters_only(
            parameters: List
    ) -> AssistanceObject:
        assistance_object = AssistanceObject()
        assistance_object.parameters = parameters
        return assistance_object

    def _init(self, data):
        self.a_id = data.get("a_id")
        self.assistance_type = data.get("assistance_type")
        self.ao_id = data.get("ao_id")
        self.user_id = data.get("user_id")
        self.timestamp = data.get("timestamp")
        self.parameters = parse_assistance_parameters(data)
        self.type = parse_data_element(data=data, key="type", parse_function=lambda d: AssistanceObjectType(d))


class AssistanceObjectType(Enum):
    ASSISTANCE_OBJECT = "assistance_object"
    ASSISTANCE_RESPONSE_OBJECT = "assistance_response_object"


class AssistanceOperation(GenericModel):
    @staticmethod
    def create_with_default_parameters(
            assistance_type_key: str, assistance_operation_key: str, ctx: AssistanceContext, a_id: str
    ) -> AssistanceOperation:
        assistance_operation = AssistanceOperation()
        assistance_operation.assistance_type_key = assistance_type_key
        assistance_operation.assistance_operation_key = assistance_operation_key
        assistance_operation.a_id = a_id
        assistance_operation.ctx = ctx
        return assistance_operation

    def _init(self, data):
        self.assistance_type_key = data.get("assistance_type_key")
        self.assistance_operation_key = data.get("assistance_operation_key")
        self.a_id = data.get("a_id")
        self.ctx = AssistanceContext(data.get("ctx"))
        self.time_of_invocation = data.get("time_of_invocation")

    def to_dict(self):
        copy = deepcopy(self)
        if type(self.ctx) is AssistanceContext:
            copy.ctx = self.ctx.parameter_dict
        return copy.__dict__


class AssistanceParameter(GenericModel):
    @staticmethod
    def create_with_default_definition_parameters(
            key: str, type: AssistanceParameterType, required: bool
    ) -> AssistanceParameter:
        assistance_parameter = AssistanceParameter()
        assistance_parameter.key = key
        assistance_parameter.type = type
        assistance_parameter.required = required
        return assistance_parameter

    @staticmethod
    def create_with_default_parameters(key: str, value: Any) -> AssistanceParameter:
        assistance_parameter = AssistanceParameter()
        assistance_parameter.key = key
        assistance_parameter.value = value
        return assistance_parameter

    def _init(self, data):
        self.key = data.get("key")
        self.type = parse_data_element(data=data, key="type", parse_function=lambda d: AssistanceParameterType(d))
        self.value = parse_data_element(data=data, key="value",
                                        parse_function=lambda d: DotDict(d) if type(d) is dict else d)
        self.required = parse_data_bool_element(data=data, key="required")
        self.allowed_values = parse_data_list_element(data=data, key="allowed_values",
                                                      parse_function=lambda d: DotDict(d) if type(d) is dict else d,
                                                      default_value=None)


class AssistanceParameterCondition(GenericModel):
    def _init(self, data):
        self.key = data.get("key")
        self.required_values = parse_data_list_element(data=data, key="required_values",
                                                       parse_function=lambda d: DotDict(d) if type(d) is dict else d)


class AssistanceParameterSearchCriteria(GenericModel):
    def _init(self, data):
        self.key = data.get("key")
        self.value = data.get("value")


class AssistanceParameterType(Enum):
    INTEGER = "integer"
    NUMBER = "number"
    OBJECT = "object"
    STRING = "string"


class AssistancePhase(GenericModel):
    @staticmethod
    def create_with_default_parameters(
            phase_number: int,
            parameters: List[AssistanceParameter],
            steps: List[AssistancePhaseStep],
    ) -> AssistancePhase:
        assistance_phase = AssistancePhase()
        assistance_phase.phase_number = phase_number
        assistance_phase.parameters = parameters
        assistance_phase.steps = steps
        return assistance_phase

    def _init(self, data):
        self.phase_number = data.get("phase_number")
        self.parameters = parse_assistance_parameters(data)
        self.duration = data.get("duration")
        self.steps = parse_data_list_element(data=data, key="steps", parse_function=lambda d: AssistancePhaseStep(d))


class AssistancePhaseStep(GenericModel):
    @staticmethod
    def create_with_default_parameters(
            operation_key: str, parameters: List[AssistanceParameter]
    ) -> AssistancePhaseStep:
        assistance_phase_step = AssistancePhaseStep()
        assistance_phase_step.operation_key = operation_key
        assistance_phase_step.parameters = parameters
        return assistance_phase_step

    def _init(self, data):
        self.operation_key = data.get("operation_key")
        self.parameters = parse_assistance_parameters(data)
        self.duration = data.get("duration")


class AssistanceState(GenericModel):
    @staticmethod
    def create_with_default_parameters(
            status: AssistanceStateStatus, phase: int = None, step: str = None
    ) -> AssistanceState:
        assistance_state = AssistanceState()
        assistance_state.status = status
        assistance_state.phase = phase
        assistance_state.step = step
        return assistance_state

    def _init(self, data):
        self.status = parse_data_element(data=data, key="status", parse_function=lambda d: AssistanceStateStatus(d))
        self.phase = data.get("phase")
        self.step = data.get("step")


class AssistanceStateStatus(Enum):
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    ABORTED = "aborted"
    COMPLETED = "completed"


class AssistanceType(GenericModel):
    @staticmethod
    def create_with_default_parameters(
            key: str,
            description: str,
            kind: KindOfAssistanceType,
            parameters: List[AssistanceParameter],
            preconditions: List[AssistanceParameterCondition],
            phases: List[AssistancePhase],
    ) -> AssistanceType:
        assistance_type = AssistanceType()
        assistance_type.key = key
        assistance_type.description = description
        assistance_type.kind = kind
        assistance_type.parameters = parameters
        assistance_type.preconditions = preconditions
        assistance_type.phases = phases
        return assistance_type

    def _init(self, data):
        self.key = data.get("key")
        self.description = data.get("description")
        self.kind = parse_data_element(data=data, key="kind", parse_function=lambda d: KindOfAssistanceType(d))
        self.parameters = parse_assistance_parameters(data)
        self.preconditions = parse_data_list_element(data=data, key="preconditions",
                                                     parse_function=lambda d: AssistanceParameterCondition(d))
        self.phases = parse_data_list_element(data=data, key="phases", parse_function=lambda d: AssistancePhase(d))


class KindOfAssistanceType(Enum):
    COOPERATIVE_ASSISTANCE = "cooperative_assistance"
    INFORMATIONAL_FEEDBACK = "informational_feedback"
    PROACTIVE_ASSISTANCE = "proactive_assistance"
    REACTIVE_ASSISTANCE = "reactive_assistance"
