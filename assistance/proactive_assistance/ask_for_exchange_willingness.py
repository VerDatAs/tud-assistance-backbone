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

from loguru import logger

from assistance import get_first_assistance_parameter_by_key
from assistance.reactive_assistance import ReactiveAssistanceProcess
from error.tutorial_module import AssistanceParameterException
from model.core.tutorial_module import (
    Assistance,
    AssistanceObject,
    AssistanceParameter,
    AssistanceStateStatus, AssistanceParameterType,
)
from model.service.assistance import (
    AssistanceContext,
    AssistanceResult,
    ASSISTANCE_OPERATION_KEY_INITIATION,
    AssistanceOperation,
    ASSISTANCE_CONTEXT_PARAMETER_KEY_STATEMENT_ID,
    ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE, ASSISTANCE_TYPE_PARAMETER_KEY_USER_ID,
    ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION, ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_OPTIONS,
    ASSISTANCE_OBJECT_PARAMETER_KEY_OPTIONS, ASSISTANCE_OBJECT_PARAMETER_OPTIONS_KEY_NO,
    ASSISTANCE_OBJECT_PARAMETER_OPTIONS_KEY_YES, ASSISTANCE_CONTEXT_PARAMETER_KEY_ASSISTANCE_OBJECTS,
    ASSISTANCE_OBJECT_PARAMETER_KEY_OPTIONS_RESPONSE, ASSISTANCE_CONTEXT_PARAMETER_KEY_A_ID,
    ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_OPTIONS, SubsequentAssistanceOperationType,
    SubsequentAssistanceOperation, ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE,
)
from service.db.assistance import read_assistance_by_a_id
from service.db.student_model import update_student_model_cooperativeness_by_user_id
from service.i18n import LOCALE_IDENTIFIER_DE, t


class AskForExchangeWillingnessAssistance(ReactiveAssistanceProcess):
    @staticmethod
    def get_key() -> str:
        return "ask_for_exchange_willingness"

    @staticmethod
    def get_parameters() -> List[AssistanceParameter] | None:
        return [
            AssistanceParameter.create_with_default_definition_parameters(
                key=ASSISTANCE_TYPE_PARAMETER_KEY_USER_ID,
                type=AssistanceParameterType.STRING,
                required=True,
            ),
        ]

    def __init__(self) -> None:
        super().__init__()
        assistance_operation_key_abort_wait_for_option_response = "abort_wait_for_option_response"
        assistance_operation_key_wait_for_option_response = "wait_for_option_response"

        self._register_operation(
            ASSISTANCE_OPERATION_KEY_INITIATION,
            AskForExchangeWillingnessAssistanceInitiationOperation(
                assistance_process=self,
                target_status=AssistanceStateStatus.IN_PROGRESS,
                subsequent_operations=[
                    SubsequentAssistanceOperation(
                        type=SubsequentAssistanceOperationType.TRIGGERED_OPERATION,
                        operation_key=assistance_operation_key_wait_for_option_response,
                    ),
                    SubsequentAssistanceOperation(
                        type=SubsequentAssistanceOperationType.SCHEDULED_OPERATION,
                        operation_key=assistance_operation_key_abort_wait_for_option_response,
                        time_to_invocation_in_s=30
                    )
                ],
            ),
        )

        self._register_operation(
            assistance_operation_key_wait_for_option_response,
            WaitForOptionsResponseOperation(
                assistance_process=self,
                target_status=AssistanceStateStatus.IN_PROGRESS,
            ),
        )
        self._register_operation(
            assistance_operation_key_abort_wait_for_option_response,
            AbortOfferAssistanceOptionsAssistanceOperation(
                assistance_process=self,
                target_status=AssistanceStateStatus.ABORTED,
                subsequent_operations=[],
                assistance_in_progress_required=True,
                delete_scheduled_operations=True,
            ),
        )


class AbortOfferAssistanceOptionsAssistanceOperation(AssistanceOperation):
    def _execute(self, ctx: AssistanceContext) -> AssistanceResult | None:
        assistance = read_assistance_by_a_id(
            ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_A_ID)
        )
        assistance.assistance_objects = [
            AssistanceObject.create_with_default_parameters(
                user_id=assistance.user_id,
                parameters=[
                    AssistanceParameter.create_with_default_parameters(
                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_OPTIONS,
                    )
                ]
            ),
            AssistanceObject.create_with_default_parameters(
                user_id=assistance.user_id,
                parameters=[
                    AssistanceParameter.create_with_default_parameters(
                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE,
                        value=t(
                            LOCALE_IDENTIFIER_DE,
                            "assistance.ask_for_exchange_willingness.operation.system_message_no_option_selected",
                        ),
                    )
                ]
            )
        ]
        return AssistanceResult(assistance=[assistance])


class AskForExchangeWillingnessAssistanceInitiationOperation(AssistanceOperation):
    def is_applicable(self, ctx: AssistanceContext) -> bool:
        try:
            ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_STATEMENT_ID)
            return False
        except AssistanceParameterException:
            # This is expected
            pass
        try:
            ctx.get_parameter(
                ASSISTANCE_TYPE_PARAMETER_KEY_USER_ID
            )
        except AssistanceParameterException:
            return False
        return True

    def _execute(self, ctx: AssistanceContext) -> AssistanceResult | None:
        user_id = ctx.get_parameter(
            ASSISTANCE_TYPE_PARAMETER_KEY_USER_ID
        )

        return AssistanceResult(
            assistance=[
                Assistance.create_with_default_parameters(
                    user_id=user_id,
                    assistance_objects=[
                        AssistanceObject.create_with_default_parameters(
                            user_id=user_id,
                            parameters=[
                                AssistanceParameter.create_with_default_parameters(
                                    key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                                    value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_OPTIONS
                                ),
                            ]
                        ),
                        AssistanceObject.create_with_default_parameters(
                            user_id=user_id,
                            parameters=[
                                AssistanceParameter.create_with_default_parameters(
                                    key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                                    value=t(
                                        LOCALE_IDENTIFIER_DE,
                                        "assistance.ask_for_exchange_willingness.operation.message_question_for_exchange_willingness",
                                    ),
                                ),
                                AssistanceParameter.create_with_default_parameters(
                                    key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPTIONS,
                                    value=[
                                        AssistanceParameter.create_with_default_parameters(
                                            key=ASSISTANCE_OBJECT_PARAMETER_OPTIONS_KEY_YES,
                                            value=t(
                                                LOCALE_IDENTIFIER_DE,
                                                "assistance.ask_for_exchange_willingness.operation.option_yes",
                                            ),
                                        ),
                                        AssistanceParameter.create_with_default_parameters(
                                            key=ASSISTANCE_OBJECT_PARAMETER_OPTIONS_KEY_NO,
                                            value=t(
                                                LOCALE_IDENTIFIER_DE,
                                                "assistance.ask_for_exchange_willingness.operation.option_no",
                                            ),
                                        ),
                                    ],
                                )
                            ],
                        )
                    ],
                )
            ]
        )


class WaitForOptionsResponseOperation(AssistanceOperation):
    def post_init(self):
        self.assistance_in_progress_required = True

    def is_applicable(self, ctx: AssistanceContext) -> bool:
        try:
            ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_STATEMENT_ID)
            return False
        except AssistanceParameterException:
            # This is expected
            pass
        try:
            received_assistance_objects = ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_ASSISTANCE_OBJECTS)
            expected_parameter_key_contained = False
            for received_assistance_object in received_assistance_objects:
                try:
                    get_first_assistance_parameter_by_key(received_assistance_object.parameters,
                                                          ASSISTANCE_OBJECT_PARAMETER_KEY_OPTIONS_RESPONSE)
                    expected_parameter_key_contained = True
                    break
                except AssistanceParameterException:
                    pass
            if not expected_parameter_key_contained:
                return False
        except AssistanceParameterException:
            return False
        return True

    def _execute(self, ctx: AssistanceContext) -> AssistanceResult | None:
        assistance = read_assistance_by_a_id(
            ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_A_ID)
        )
        received_assistance_objects = ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_ASSISTANCE_OBJECTS)
        provided_object_value = None
        for received_assistance_object in received_assistance_objects:
            try:
                provided_object_value = get_first_assistance_parameter_by_key(
                    received_assistance_object.parameters, ASSISTANCE_OBJECT_PARAMETER_KEY_OPTIONS_RESPONSE).value
                break
            except AssistanceParameterException:
                pass
        if provided_object_value is None:
            return None

        if provided_object_value == ASSISTANCE_OBJECT_PARAMETER_OPTIONS_KEY_YES or provided_object_value == ASSISTANCE_OBJECT_PARAMETER_OPTIONS_KEY_NO:
            update_student_model_cooperativeness_by_user_id(
                user_id=assistance.user_id,
                cooperativeness=provided_object_value == ASSISTANCE_OBJECT_PARAMETER_OPTIONS_KEY_YES)

            assistance.assistance_objects = [
                AssistanceObject.create_with_default_parameters(
                    user_id=assistance.user_id,
                    parameters=[
                        AssistanceParameter.create_with_default_parameters(
                            key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                            value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_OPTIONS,
                        )
                    ]
                ),
                AssistanceObject.create_with_default_parameters(
                    user_id=assistance.user_id,
                    parameters=[
                        AssistanceParameter.create_with_default_parameters(
                            key=ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE,
                            value=t(
                                LOCALE_IDENTIFIER_DE,
                                "assistance.ask_for_exchange_willingness.operation.system_message_confirmation_considered_in_future" if provided_object_value == ASSISTANCE_OBJECT_PARAMETER_OPTIONS_KEY_YES else "assistance.ask_for_exchange_willingness.operation.system_message_confirmation_not_considered_in_future",
                            ),
                        )
                    ]
                ),
            ]
            self.delete_scheduled_operations = True
            self.subsequent_operations = []
            self.prevent_progress = False
            self.target_status = AssistanceStateStatus.COMPLETED
            return AssistanceResult(assistance=[assistance])
        else:
            logger.warning(f"Received unknown options response {provided_object_value}")
            self.prevent_progress = True
            return None
