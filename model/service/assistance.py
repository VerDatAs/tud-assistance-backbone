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

from abc import abstractmethod, ABC
from enum import Enum
from typing import List

from loguru import logger

from assistance import get_first_assistance_parameter_by_key, replace_or_add_assistance_parameters_by_key
from error.tutorial_module import (
    AssistanceParameterException,
    AssistanceOperationException,
    AssistanceOperationCanNotBeScheduledException,
)
from model.core.tutorial_module import (
    Assistance,
    AssistanceOperation as AssistanceOperationModel,
    AssistanceParameter,
    AssistanceType,
    AssistanceParameterCondition,
    KindOfAssistanceType,
    AssistanceState,
    AssistanceContext,
    AssistanceObjectType,
    AssistanceObject,
)
from model.core.tutorial_module import (
    AssistancePhase as AssistancePhaseModel,
    AssistanceStateStatus,
)
from model.core.tutorial_module import (
    AssistancePhaseStep as AssistancePhaseStepModel,
)
from service.administration import debug
from service.administration import read_setting_by_key, SETTING_KEY_DEBUG_SCHEDULED_ASSISTANCE_TIME_FACTOR
from service.db.assistance import (
    read_assistance_by_a_id,
    create_assistance,
    update_assistance_adding_assistance_objects,
    update_assistance_by_a_id_reset_next_operation_keys,
)
from service.db.assistance_operation import (
    create_assistance_operation_for_scheduled_invocation, delete_assistance_operations_by_a_id,
)
from service.i18n import t

ASSISTANCE_CONTEXT_PARAMETER_KEY_A_ID = "a_id"
ASSISTANCE_CONTEXT_PARAMETER_KEY_ASSISTANCE_OBJECTS = "assistance_objects"
ASSISTANCE_CONTEXT_PARAMETER_KEY_STATEMENT_ID = "statement_id"
ASSISTANCE_OPERATION_KEY_ABORTION = "abortion"
ASSISTANCE_OPERATION_KEY_INITIATION = "initiation"
ASSISTANCE_OPERATION_PARAMETER_KEY_TITLE = "title"
ASSISTANCE_OBJECT_PARAMETER_KEY_CLICK_NOTIFICATION_RESPONSE = "click_notification_response"
ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE = "message"
ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE_RESPONSE = "message_response"
ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION = "operation"
ASSISTANCE_OBJECT_PARAMETER_KEY_OPTIONS = "options"
ASSISTANCE_OBJECT_PARAMETER_KEY_OPTIONS_RESPONSE = "options_response"
ASSISTANCE_OBJECT_PARAMETER_KEY_PEER_SOLUTION = "peer_solution"
ASSISTANCE_OBJECT_PARAMETER_KEY_QUESTION_FOR_AI_RESPONSE = "question_for_ai_response"
ASSISTANCE_OBJECT_PARAMETER_KEY_RELATED_USERS = "related_users"
ASSISTANCE_OBJECT_PARAMETER_KEY_REQUIRE_CLICK_NOTIFICATION = "require_click_notification"
ASSISTANCE_OBJECT_PARAMETER_KEY_SOLUTION_RESPONSE = "solution_response"
ASSISTANCE_OBJECT_PARAMETER_KEY_SOLUTION_TEMPLATE = "solution_template"
ASSISTANCE_OBJECT_PARAMETER_KEY_STATE_UPDATE = "state_update"
ASSISTANCE_OBJECT_PARAMETER_KEY_STATE_UPDATE_RESPONSE = "state_update_response"
ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE = "system_message"
ASSISTANCE_OBJECT_PARAMETER_KEY_URI = "uri"
ASSISTANCE_OBJECT_PARAMETER_KEY_USER_ID = "user_id"
ASSISTANCE_OBJECT_PARAMETER_KEY_USER_MESSAGE = "user_message"
ASSISTANCE_OBJECT_PARAMETER_OPTIONS_KEY_ACCEPTED = "accepted"
ASSISTANCE_OBJECT_PARAMETER_OPTIONS_KEY_DECLINED = "declined"
ASSISTANCE_OBJECT_PARAMETER_OPTIONS_KEY_NO = "no"
ASSISTANCE_OBJECT_PARAMETER_OPTIONS_KEY_PEER_EXCHANGE = "peer_exchange"
ASSISTANCE_OBJECT_PARAMETER_OPTIONS_KEY_TRADITIONAL_FEEDBACK = "traditional_feedback"
ASSISTANCE_OBJECT_PARAMETER_OPTIONS_KEY_YES = "yes"
ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ASK_AI = "ask_ai"
ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_ABORT_EXCHANGE_COMMAND = "disable_abort_exchange_command"
ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_CHAT = "disable_chat"
ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_NOTES = "disable_notes"
ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_NOTES_COMMAND = "disable_notes_command"
ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_NOTES_INPUT = "disable_notes_input"
ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_OPTIONS = "disable_options"
ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_PEER_SOLUTION = "disable_peer_solution"
ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_PEER_SOLUTION_COMMAND = "disable_peer_solution_command"
ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_ABORT_EXCHANGE_COMMAND = "enable_abort_exchange_command"
ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_CHAT = "enable_chat"
ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_NOTES = "enable_notes"
ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_NOTES_COMMAND = "enable_notes_command"
ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_NOTES_INPUT = "enable_notes_input"
ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_OPTIONS = "enable_options"
ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_PEER_SOLUTION = "enable_peer_solution"
ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_PEER_SOLUTION_COMMAND = "enable_peer_solution_command"
ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_RESET_NOTES = "reset_notes"
ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_SEND_SOLUTION = "send_solution"
ASSISTANCE_OBJECT_PARAMETER_VALUE_STATE_UPDATE_RESPONSE_STANDBY = "standby"
ASSISTANCE_PARAMETER_KEY_RELATED_USER_IDS = "related_user_ids"
ASSISTANCE_PARAMETER_KEY_USER_ID_TO_STATE = "user_states"
ASSISTANCE_TYPE_PARAMETER_KEY_USER_IDS_COLLABORATORS = "collaborators"
ASSISTANCE_TYPE_PARAMETER_KEY_USER_ID = "user_id"
ASSISTANCE_TYPE_PARAMETER_KEY_USER_ID_INITIATOR = "initiator"


class AssistanceOperation(ABC):
    def __init__(
            self,
            assistance_process: AssistanceProcess,
            target_status: AssistanceStateStatus = None,
            parameters: List[AssistanceParameter] = None,
            subsequent_operations: List[SubsequentAssistanceOperation] = None,
            assistance_in_progress_required: bool = False,
            delete_scheduled_operations: bool = False,
            reset_next_operation_keys: bool = False,
            prevent_progress: bool = False,
            related_user_ids: List[str] = None,
            phase: int = None,
            step: str = None,
            state_update_status_to_send: List[AssistanceStateStatus] = None,
            send_state_update_to_related_users: bool = True,
    ) -> None:
        super().__init__()
        self.assistance_process = assistance_process
        self.target_status = target_status
        self.parameters = [] if parameters is None else parameters
        self.subsequent_operations = subsequent_operations
        self.assistance_in_progress_required = assistance_in_progress_required
        self.delete_scheduled_operations = delete_scheduled_operations
        self.reset_next_operation_keys = reset_next_operation_keys
        self.prevent_progress = prevent_progress
        self.related_user_ids = related_user_ids
        self.phase = phase
        self.step = step
        self.state_update_status_to_send = state_update_status_to_send
        self.send_state_update_to_related_users = send_state_update_to_related_users

        self.post_init()

    def post_init(self):
        pass

    def is_applicable(self, ctx: AssistanceContext) -> bool:
        if not self.assistance_in_progress_required:
            return True
        try:
            ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_A_ID)
            read_assistance_by_a_id(
                ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_A_ID)
            )
        except AssistanceParameterException:
            return False
        return True

    def execute(
            self, ctx: AssistanceContext, phase: int = None, step: str = None
    ) -> AssistanceResult | None:
        self.phase = phase
        self.step = step
        self.reset_next_operation_keys = self.reset_next_operation_keys or self.subsequent_operations is not None

        result = self._execute(ctx=ctx)
        logger.info(f"Executed operation {self.__class__.__name__}. prevent_progress is {self.prevent_progress}")

        subsequent_triggered_operations = [] if self.prevent_progress else AssistanceOperation._filter_subsequent_operations_by_type(
            self.subsequent_operations, SubsequentAssistanceOperationType.TRIGGERED_OPERATION)
        subsequent_scheduled_operations = [] if self.prevent_progress else AssistanceOperation._filter_subsequent_operations_by_type(
            self.subsequent_operations, SubsequentAssistanceOperationType.SCHEDULED_OPERATION)

        # Check if next operation keys have to be reset
        if self.assistance_in_progress_required and self.reset_next_operation_keys and not self.prevent_progress:
            update_assistance_by_a_id_reset_next_operation_keys(
                ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_A_ID)
            )
        if self.assistance_in_progress_required and self.delete_scheduled_operations and not self.prevent_progress:
            delete_assistance_operations_by_a_id(
                ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_A_ID)
            )

        assistance_to_return = []
        if result is not None and result.assistance is not None and len(result.assistance) != 0:
            for assistance in result.assistance:
                processed_assistance_result = self._process_assistance_result(
                    assistance_to_process=assistance, ctx=ctx,
                    subsequent_scheduled_operations=subsequent_scheduled_operations,
                    subsequent_triggered_operations=subsequent_triggered_operations)
                if processed_assistance_result is None:
                    continue
                assistance_to_return.append(processed_assistance_result)
        else:
            self._process_assistance_result(
                assistance_to_process=None, ctx=ctx,
                subsequent_scheduled_operations=subsequent_scheduled_operations,
                subsequent_triggered_operations=subsequent_triggered_operations)

        if result is None:
            return None

        result.assistance = assistance_to_return
        return result

    def _process_assistance_result(
            self, assistance_to_process: Assistance | None, ctx: AssistanceContext,
            subsequent_scheduled_operations: List[SubsequentAssistanceOperation],
            subsequent_triggered_operations: List[SubsequentAssistanceOperation]) -> Assistance | None:
        if assistance_to_process is None:
            if self.assistance_in_progress_required:
                assistance = read_assistance_by_a_id(ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_A_ID))
                assistance.assistance_objects = []
            else:
                return None
        else:
            assistance = assistance_to_process

        # Determine state update
        if (
                self.target_status is not None
                and self.phase is not None
                and self.step is not None
        ):
            assistance_state_status_update = (
                self.target_status
                if assistance.assistance_state is not None and assistance.assistance_state.status is not None and self.target_status != assistance.assistance_state.status
                else assistance.assistance_state.status if assistance.assistance_state is not None and assistance.assistance_state.status is not None
                else AssistanceStateStatus.INITIATED
            )
            assistance_state_phase_update = (
                self.phase
                if assistance.assistance_state is not None and assistance.assistance_state.phase is not None and self.phase != assistance.assistance_state.phase
                else assistance.assistance_state.phase if assistance.assistance_state is not None and assistance.assistance_state.phase is not None
                else 1
            )
            assistance_state_step_update = (
                self.step
                if assistance.assistance_state is not None and assistance.assistance_state.step is not None and self.step != assistance.assistance_state.step
                else assistance.assistance_state.step if assistance.assistance_state is not None and assistance.assistance_state.step is not None
                else ASSISTANCE_OPERATION_KEY_INITIATION
            )

            status_update_assistance_objects = self._compute_state_update_assistance_objects(
                assistance=assistance, status_update=assistance_state_status_update,
                phase_update=assistance_state_phase_update, step_update=assistance_state_step_update)

            assistance.assistance_objects = status_update_assistance_objects + assistance.assistance_objects

            # Set user states
            if not (not status_update_assistance_objects):
                try:
                    user_states = get_first_assistance_parameter_by_key(
                        assistance.parameters,
                        ASSISTANCE_PARAMETER_KEY_USER_ID_TO_STATE).value
                except AssistanceParameterException:
                    user_states = {}

                for status_update_assistance_object in status_update_assistance_objects:
                    user_states[
                        status_update_assistance_object.user_id] = get_first_assistance_parameter_by_key(
                        status_update_assistance_object.parameters,
                        ASSISTANCE_OBJECT_PARAMETER_KEY_STATE_UPDATE).value

                assistance.parameters = replace_or_add_assistance_parameters_by_key(
                    AssistanceParameter.create_with_default_parameters(
                        ASSISTANCE_PARAMETER_KEY_USER_ID_TO_STATE,
                        user_states,
                    ), assistance.parameters
                )
        elif self.target_status is not None:
            assistance_state_status_update = (
                self.target_status
                if assistance.assistance_state is not None and assistance.assistance_state.status is not None and self.target_status != assistance.assistance_state.status
                else assistance.assistance_state.status if assistance.assistance_state is not None and assistance.assistance_state.status is not None
                else AssistanceStateStatus.INITIATED
            )

            if self.state_update_status_to_send is None:
                self.state_update_status_to_send = [AssistanceStateStatus.ABORTED, AssistanceStateStatus.COMPLETED]

            status_update_assistance_objects = self._compute_state_update_assistance_objects(
                assistance=assistance, status_update=assistance_state_status_update,
                phase_update=None, step_update=None)

            assistance.assistance_objects = status_update_assistance_objects + assistance.assistance_objects

        # Set assistance properties
        if not self.prevent_progress:
            assistance.assistance_state = (
                AssistanceState.create_with_default_parameters(
                    status=self.target_status, phase=self.phase, step=self.step
                )
            )
            assistance.next_operation_keys = list(map(lambda o: o.operation_key, subsequent_triggered_operations))
            if assistance.a_id is not None:
                logger.info(f"Set next operation keys for {assistance.a_id} to {assistance.next_operation_keys}")
        # Set type of new assistance objects
        for assistance_object in assistance.assistance_objects:
            assistance_object.assistance_type = self.assistance_process.get_key()
            if assistance_object.type is not None:
                continue
            assistance_object.type = AssistanceObjectType.ASSISTANCE_OBJECT
        # Create new assistance
        if assistance.a_id is None:
            logger.info(f"Create new assistance process of type {self.assistance_process.get_key()}")
            assistance.type_key = self.assistance_process.get_key()
            persisted_assistance = create_assistance(assistance)
        # or update existing assistance
        else:
            logger.info(f"Update assistance {assistance.a_id} of type {self.assistance_process.get_key()}")
            previous_assistance = read_assistance_by_a_id(assistance.a_id)
            previous_assistance_object_ao_ids = list(
                map(
                    lambda assistance_object: assistance_object.ao_id,
                    previous_assistance.assistance_objects,
                )
            )
            persisted_assistance = (
                update_assistance_adding_assistance_objects(assistance)
            )
            persisted_assistance.assistance_objects = list(
                filter(
                    lambda assistance_object: assistance_object.ao_id
                                              not in previous_assistance_object_ao_ids,
                    persisted_assistance.assistance_objects,
                )
            )

        # Schedule operations
        for subsequent_scheduled_operation in subsequent_scheduled_operations:
            self.assistance_process.schedule_operation(
                operation_key=subsequent_scheduled_operation.operation_key,
                ctx=AssistanceContext(
                    {
                        ASSISTANCE_CONTEXT_PARAMETER_KEY_A_ID: persisted_assistance.a_id
                    }
                ),
                time_to_invocation_in_s=subsequent_scheduled_operation.time_to_invocation_in_s,
                a_id=persisted_assistance.a_id
            )

        return persisted_assistance

    @staticmethod
    def _filter_subsequent_operations_by_type(
            subsequent_operations: List[SubsequentAssistanceOperation] | None,
            type: SubsequentAssistanceOperationType) -> List[SubsequentAssistanceOperation]:
        if subsequent_operations is None:
            return []
        return list(filter(lambda o: o.type == type, subsequent_operations))

    def _compute_state_update_assistance_objects(
            self, assistance: Assistance, status_update: AssistanceStateStatus,
            phase_update: int | None, step_update: str | None) -> List[AssistanceObject]:
        status_update_assistance_objects = []
        if self.state_update_status_to_send is not None and status_update not in self.state_update_status_to_send:
            return status_update_assistance_objects

        ids_of_users_to_update = [assistance.user_id]

        if self.send_state_update_to_related_users:
            if self.related_user_ids is not None:
                ids_of_users_to_update = self.related_user_ids
            elif not (not assistance.parameters):
                related_user_ids = next((
                    parameter.value
                    for parameter in assistance.parameters
                    if parameter.key
                       == ASSISTANCE_PARAMETER_KEY_RELATED_USER_IDS
                ), None)
                if related_user_ids is not None:
                    ids_of_users_to_update = related_user_ids

        for id_of_user_to_update in ids_of_users_to_update:
            status_update_assistance_objects.append(
                AssistanceObject.create_with_default_parameters(
                    user_id=id_of_user_to_update,
                    parameters=[
                        AssistanceParameter.create_with_default_parameters(
                            key=ASSISTANCE_OBJECT_PARAMETER_KEY_STATE_UPDATE,
                            value={
                                k: v
                                for k, v in AssistanceState.create_with_default_parameters(
                                    status=status_update,
                                    phase=phase_update,
                                    step=step_update,
                                )
                                .to_dict()
                                .items()
                                if v is not None
                            },
                        )
                    ],
                )
            )

        return status_update_assistance_objects

    def _execute(self, ctx: AssistanceContext) -> AssistanceResult | None:
        return None


class AssistanceOperationSchedule:
    def __init__(self, time_to_invocation_in_s: float):
        self.time_to_invocation_in_s = time_to_invocation_in_s


class AssistancePhase:
    def __init__(
            self, parameters: List[AssistanceParameter], steps: List[AssistancePhaseStep]
    ):
        self.parameters = parameters
        self.steps = steps


class AssistancePhaseStep:
    def __init__(
            self,
            operation_key: str,
            parameters: List[AssistanceParameter],
            operation: AssistanceOperation,
            schedule: AssistanceOperationSchedule = None,
    ):
        self.operation_key = operation_key
        self.parameters = parameters
        self.operation = operation
        self.schedule = schedule


class AssistanceProcess(ABC):
    def __init__(self):
        self._registered_phases = []
        self._registered_operations = {}
        self._registered_operation_keys_to_phase_number = {}
        self.registered_operation_keys_to_step_number = {}

    @staticmethod
    @abstractmethod
    def get_key() -> str:
        """Get an identifier which uniquely identifies an assistance type."""

    @staticmethod
    @abstractmethod
    def get_kind() -> KindOfAssistanceType:
        """Get an identifier which uniquely identifies the kind of assistance type."""

    def get_description(self) -> str:
        """Get a description of the assistance type including the information when is it provided."""
        return t("en", f"assistance.{self.get_key()}.description")

    @staticmethod
    def get_parameters() -> List[AssistanceParameter] | None:
        """Get the parameters for the assistance."""
        return None

    @staticmethod
    def get_preconditions() -> List[AssistanceParameterCondition] | None:
        """Get the preconditions for the assistance."""
        return None

    def get_type(self) -> AssistanceType:
        phases = []
        for phase_index, phase in enumerate(self._registered_phases):
            steps = []
            steps_duration_sum = 0.0
            for step_index, step in enumerate(phase.steps):
                step_spec = AssistancePhaseStepModel.create_with_default_parameters(
                    operation_key=step.operation_key,
                    parameters=step.parameters,
                )
                # Check whether it is the last step
                if step_index == len(phase.steps) - 1 and phase_index == len(
                        self._registered_phases
                ) - 1:
                    steps.append(step_spec)
                    continue
                # Check whether the next step is scheduled
                next_step = (
                    phase.steps[step_index + 1]
                    if step_index != len(phase.steps) - 1
                    else self._registered_phases[phase_index + 1].steps[0]
                )
                if next_step.schedule is None:
                    steps.append(step_spec)
                    continue

                step_spec.duration = next_step.schedule.time_to_invocation_in_s
                steps_duration_sum += next_step.schedule.time_to_invocation_in_s
                steps.append(step_spec)

            phase_spec = AssistancePhaseModel.create_with_default_parameters(
                phase_number=phase_index + 1,
                parameters=phase.parameters,
                steps=steps,
            )
            if steps_duration_sum != 0:
                phase_spec.duration = steps_duration_sum
            phases.append(phase_spec)

        return AssistanceType.create_with_default_parameters(
            key=self.get_key(),
            description=self.get_description(),
            kind=self.get_kind(),
            parameters=self.get_parameters(),
            preconditions=self.get_preconditions(),
            phases=phases,
        )

    def check_applicability_and_execute_operation(
            self, operation_key: str, ctx: AssistanceContext
    ) -> AssistanceResult | None:
        if not self.__is_operation_registered(operation_key):
            raise AssistanceOperationException(
                f"Operation '{operation_key}' not registered!"
            )
        logger.info(f"Check applicability of {operation_key} for {self.get_key()}")
        if not self._registered_operations[operation_key].is_applicable(ctx):
            logger.debug(f"Operation {operation_key} is not applicable for {self.get_key()}")
            return None
        logger.info(f"Execute {operation_key} for {self.get_key()}")
        return self._registered_operations[operation_key].execute(
            ctx=ctx,
            phase=(
                self._registered_operation_keys_to_phase_number[operation_key]
                if operation_key in self._registered_operation_keys_to_phase_number
                else None
            ),
            step=operation_key,
        )

    def schedule_operation(
            self, operation_key: str, ctx: AssistanceContext, time_to_invocation_in_s: float, a_id: str
    ) -> None:
        if not self.__is_operation_registered(operation_key):
            raise AssistanceOperationException(
                f"Operation '{operation_key}' not registered!"
            )
        if not ctx.context_can_be_persisted:
            raise AssistanceOperationCanNotBeScheduledException()

        debug_scheduled_assistance_time_factor = 1
        if debug():
            stored_debug_scheduled_assistance_time_factor = read_setting_by_key(
                SETTING_KEY_DEBUG_SCHEDULED_ASSISTANCE_TIME_FACTOR)
            if stored_debug_scheduled_assistance_time_factor is not None:
                debug_scheduled_assistance_time_factor = stored_debug_scheduled_assistance_time_factor.value
        create_assistance_operation_for_scheduled_invocation(
            assistance_operation=AssistanceOperationModel.create_with_default_parameters(
                assistance_type_key=self.get_key(),
                assistance_operation_key=operation_key,
                ctx=ctx,
                a_id=a_id
            ),
            time_to_invocation_in_s=time_to_invocation_in_s * debug_scheduled_assistance_time_factor,
        )

    def _register_phases(self, phases: List[AssistancePhase]):
        operations_to_register = {}
        keys_of_operations_to_register_to_phase_number = {}
        keys_of_operations_to_register_to_step_number = {}

        step_number = 0
        for phase_index, phase in enumerate(phases):
            for step_index, step in enumerate(phase.steps):
                step_number += 1
                if step.operation_key in operations_to_register.keys():
                    raise AssistanceOperationException(
                        f"Operation '{step.operation_key}' already registered!"
                    )
                keys_of_operations_to_register_to_phase_number[step.operation_key] = (
                        phase_index + 1
                )
                keys_of_operations_to_register_to_step_number[step.operation_key] = step_number
                operation_to_register = step.operation
                # Check if this is the first step of the assistance process
                if phase_index != 0 or step_index != 0:
                    operation_to_register.assistance_in_progress_required = True
                # Check if this is the last step of the assistance process
                if (
                        phase_index == len(phases) - 1
                        and step_index == len(phase.steps) - 1
                ):
                    operations_to_register[step.operation_key] = operation_to_register
                    continue
                next_step = (
                    phase.steps[step_index + 1]
                    if step_index != len(phase.steps) - 1
                    else phases[phase_index + 1].steps[0]
                )

                if operation_to_register.subsequent_operations is None:
                    operation_to_register.subsequent_operations = []
                # Check if the next step is triggered or scheduled
                if next_step.schedule is None:
                    operation_to_register.subsequent_operations.append(
                        SubsequentAssistanceOperation(
                            type=SubsequentAssistanceOperationType.TRIGGERED_OPERATION,
                            operation_key=next_step.operation_key,
                        )
                    )
                else:
                    operation_to_register.subsequent_operations.append(
                        SubsequentAssistanceOperation(
                            type=SubsequentAssistanceOperationType.SCHEDULED_OPERATION,
                            operation_key=next_step.operation_key,
                            time_to_invocation_in_s=next_step.schedule.time_to_invocation_in_s,
                        )
                    )
                operations_to_register[step.operation_key] = operation_to_register
                continue

        self._registered_operations |= operations_to_register
        self._registered_operation_keys_to_phase_number = keys_of_operations_to_register_to_phase_number
        self.registered_operation_keys_to_step_number = keys_of_operations_to_register_to_step_number
        self._registered_phases = phases

    def _register_operation(
            self, operation_key: str, operation: AssistanceOperation
    ) -> None:
        if self.__is_operation_registered(operation_key):
            raise AssistanceOperationException(
                f"Operation '{operation_key}' already registered!"
            )
        self._registered_operations[operation_key] = operation

    def __is_operation_registered(self, operation_key: str) -> bool:
        return operation_key in self._registered_operations


class AssistanceRequest:
    def __init__(
            self,
            assistance_type_key: str,
            assistance_operation_key: str,
            ctx: AssistanceContext,
    ):
        self.assistance_type_key = assistance_type_key
        self.assistance_operation_key = assistance_operation_key
        self.ctx = ctx


class AssistanceResult:
    def __init__(
            self,
            assistance: List[Assistance] | None,
            assistance_requests: List[AssistanceRequest] | None = None,
            prepend_assistance_from_requests: bool = False
    ):
        self.assistance = [] if assistance is None else assistance
        self.assistance_requests = (
            [] if assistance_requests is None else assistance_requests
        )
        self.prepend_assistance_from_requests = prepend_assistance_from_requests


class SubsequentAssistanceOperation:
    def __init__(
            self,
            type: SubsequentAssistanceOperationType,
            operation_key: str,
            time_to_invocation_in_s: float = None,
    ) -> None:
        self.type = type
        self.operation_key = operation_key
        self.time_to_invocation_in_s = time_to_invocation_in_s


class SubsequentAssistanceOperationType(Enum):
    TRIGGERED_OPERATION = "TRIGGERED_OPERATION"
    SCHEDULED_OPERATION = "SCHEDULED_OPERATION"
