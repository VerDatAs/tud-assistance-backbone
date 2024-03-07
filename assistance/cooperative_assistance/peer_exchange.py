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

from assistance import (
    get_first_assistance_parameter_by_key,
    get_assistance_parameters_by_key, )
from assistance.cooperative_assistance import CooperativeAssistanceProcess
from error.tutorial_module import AssistanceParameterException
from model.core.tutorial_module import (
    AssistanceContext,
    Assistance,
    AssistanceObject,
    AssistanceParameter,
    AssistanceStateStatus,
    AssistanceParameterType,
)
from model.service.assistance import (
    AssistanceOperation,
    AssistanceResult,
    ASSISTANCE_CONTEXT_PARAMETER_KEY_STATEMENT_ID,
    ASSISTANCE_CONTEXT_PARAMETER_KEY_A_ID,
    ASSISTANCE_OPERATION_KEY_INITIATION,
    SubsequentAssistanceOperationType,
    SubsequentAssistanceOperation,
    ASSISTANCE_CONTEXT_PARAMETER_KEY_ASSISTANCE_OBJECTS,
    ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE_RESPONSE,
    ASSISTANCE_PARAMETER_KEY_RELATED_USER_IDS, ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE,
    ASSISTANCE_OBJECT_PARAMETER_KEY_USER_MESSAGE, ASSISTANCE_TYPE_PARAMETER_KEY_USER_ID_INITIATOR,
    ASSISTANCE_TYPE_PARAMETER_KEY_USER_IDS_COLLABORATORS, ASSISTANCE_OBJECT_PARAMETER_KEY_STATE_UPDATE_RESPONSE,
    ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE, ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
    ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_CHAT,
    ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_ABORT_EXCHANGE_COMMAND,
    ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_CHAT,
    ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_ABORT_EXCHANGE_COMMAND,
    ASSISTANCE_OBJECT_PARAMETER_KEY_RELATED_USERS, ASSISTANCE_OPERATION_KEY_ABORTION,
)
from service.db.assistance import read_assistance_by_a_id
from service.i18n import LOCALE_IDENTIFIER_DE, t


class PeerExchangeAssistance(CooperativeAssistanceProcess):
    @staticmethod
    def get_key() -> str:
        return "peer_exchange"

    @staticmethod
    def get_parameters() -> List[AssistanceParameter] | None:
        return [
            AssistanceParameter.create_with_default_definition_parameters(
                key=ASSISTANCE_TYPE_PARAMETER_KEY_USER_ID_INITIATOR,
                type=AssistanceParameterType.STRING,
                required=True,
            ),
            AssistanceParameter.create_with_default_definition_parameters(
                key=ASSISTANCE_TYPE_PARAMETER_KEY_USER_IDS_COLLABORATORS,
                type=AssistanceParameterType.OBJECT,
                required=True,
            ),
        ]

    def __init__(self) -> None:
        super().__init__()

        send_message_to_peer = "send_message_to_peer"
        finish_exchange = "finish_exchange"

        self._register_operation(
            ASSISTANCE_OPERATION_KEY_INITIATION,
            PeerExchangeAssistanceInitiationOperation(
                assistance_process=self,
                target_status=AssistanceStateStatus.IN_PROGRESS,
                subsequent_operations=[
                    SubsequentAssistanceOperation(
                        type=SubsequentAssistanceOperationType.TRIGGERED_OPERATION,
                        operation_key=send_message_to_peer,
                    ),
                    SubsequentAssistanceOperation(
                        type=SubsequentAssistanceOperationType.TRIGGERED_OPERATION,
                        operation_key=finish_exchange,
                    )
                ],
            ),
        )
        self._register_operation(
            send_message_to_peer,
            PeerExchangeAssistanceForwardMessageToPeerOperation(
                assistance_process=self,
                prevent_progress=True,
            ),
        )
        self._register_operation(
            finish_exchange,
            FinishPeerExchangeOperation(
                assistance_process=self,
                target_status=AssistanceStateStatus.COMPLETED,
                delete_scheduled_operations=True,
                subsequent_operations=[]
            ),
        )
        self._register_operation(
            ASSISTANCE_OPERATION_KEY_ABORTION,
            AbortPeerExchangeOperation(
                assistance_process=self,
                target_status=AssistanceStateStatus.ABORTED,
                subsequent_operations=[],
                assistance_in_progress_required=True,
                delete_scheduled_operations=True,
            ),
        )


class AbortPeerExchangeOperation(AssistanceOperation):
    def _execute(self, ctx: AssistanceContext) -> AssistanceResult | None:
        assistance = read_assistance_by_a_id(
            ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_A_ID)
        )
        related_user_ids = get_first_assistance_parameter_by_key(
            assistance.parameters,
            ASSISTANCE_PARAMETER_KEY_RELATED_USER_IDS,
        ).value
        parameters_to_send = [
            AssistanceParameter.create_with_default_parameters(
                key=ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE,
                value=t(LOCALE_IDENTIFIER_DE,
                        'assistance.peer_exchange.operation.system_message_exchange_finished'),
            ),
            AssistanceParameter.create_with_default_parameters(
                key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_CHAT
            ),
            AssistanceParameter.create_with_default_parameters(
                key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_ABORT_EXCHANGE_COMMAND
            ),
        ]
        assistance.assistance_objects = []
        for related_user_id in related_user_ids:
            assistance.assistance_objects += [
                AssistanceObject.create_with_default_parameters(
                    user_id=related_user_id,
                    parameters=[parameter_to_send]
                )
                for parameter_to_send in parameters_to_send]
        return AssistanceResult(assistance=[assistance])


class PeerExchangeAssistanceInitiationOperation(AssistanceOperation):
    def is_applicable(self, ctx: AssistanceContext) -> bool:
        try:
            ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_STATEMENT_ID)
            return False
        except AssistanceParameterException:
            # This is expected
            pass
        try:
            ctx.get_parameter(
                ASSISTANCE_TYPE_PARAMETER_KEY_USER_ID_INITIATOR
            )
            ctx.get_parameter(
                ASSISTANCE_TYPE_PARAMETER_KEY_USER_IDS_COLLABORATORS
            )
        except AssistanceParameterException:
            return False
        return True

    def _execute(self, ctx: AssistanceContext) -> AssistanceResult | None:
        user_id = ctx.get_parameter(
            ASSISTANCE_TYPE_PARAMETER_KEY_USER_ID_INITIATOR
        )
        related_user_ids = ctx.get_parameter(
            ASSISTANCE_TYPE_PARAMETER_KEY_USER_IDS_COLLABORATORS
        )

        assistance_objects_to_send = []
        for related_user_id in related_user_ids:
            assistance_objects_to_send += [
                AssistanceObject.create_with_default_parameters(
                    user_id=related_user_id,
                    parameters=[
                        AssistanceParameter.create_with_default_parameters(
                            key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                            value=t(LOCALE_IDENTIFIER_DE,
                                    'assistance.peer_exchange.operation.system_message_connected_with_peer'),
                        ),
                        AssistanceParameter.create_with_default_parameters(
                            ASSISTANCE_OBJECT_PARAMETER_KEY_RELATED_USERS,
                            related_user_ids,
                        ),
                    ]
                ),
                AssistanceObject.create_with_default_parameters(
                    user_id=related_user_id,
                    parameters=[
                        AssistanceParameter.create_with_default_parameters(
                            key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                            value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_CHAT
                        ),
                    ]
                ),
                AssistanceObject.create_with_default_parameters(
                    user_id=related_user_id,
                    parameters=[
                        AssistanceParameter.create_with_default_parameters(
                            key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                            value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_ABORT_EXCHANGE_COMMAND
                        ),
                    ]
                ),
            ]
        assistance_objects_to_send.append(
            AssistanceObject.create_with_default_parameters(
                user_id=user_id,
                parameters=[
                    AssistanceParameter.create_with_default_parameters(
                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                        value=t(LOCALE_IDENTIFIER_DE,
                                'assistance.peer_exchange.operation.message_exchange_hint'),
                    ),
                ]
            )
        )

        assistance = Assistance.create_with_default_parameters(
            user_id=user_id,
            assistance_objects=assistance_objects_to_send,
        )
        assistance.parameters = [
            AssistanceParameter.create_with_default_parameters(
                ASSISTANCE_PARAMETER_KEY_RELATED_USER_IDS,
                related_user_ids,
            )
        ]

        return AssistanceResult(assistance=[assistance])


class PeerExchangeAssistanceForwardMessageToPeerOperation(AssistanceOperation):
    def post_init(self):
        self.assistance_in_progress_required = True

    def is_applicable(self, ctx: AssistanceContext) -> bool:
        if not super().is_applicable(ctx):
            return False
        try:
            ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_ASSISTANCE_OBJECTS)
        except AssistanceParameterException:
            return False
        try:
            received_assistance_objects = ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_ASSISTANCE_OBJECTS)
            expected_parameter_key_contained = False
            for received_assistance_object in received_assistance_objects:
                try:
                    get_first_assistance_parameter_by_key(received_assistance_object.parameters,
                                                          ASSISTANCE_OBJECT_PARAMETER_KEY_STATE_UPDATE_RESPONSE)
                    expected_parameter_key_contained = True
                    break
                except AssistanceParameterException:
                    pass
            if not expected_parameter_key_contained:
                return True
        except AssistanceParameterException:
            return False
        return False

    def _execute(self, ctx: AssistanceContext) -> AssistanceResult | None:
        assistance = read_assistance_by_a_id(
            ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_A_ID)
        )
        related_user_ids = get_first_assistance_parameter_by_key(
            assistance.parameters,
            ASSISTANCE_PARAMETER_KEY_RELATED_USER_IDS,
        ).value
        received_assistance_objects = ctx.get_parameter(
            ASSISTANCE_CONTEXT_PARAMETER_KEY_ASSISTANCE_OBJECTS
        )

        assistance_objects = []
        for received_assistance_object in received_assistance_objects:
            user_id = received_assistance_object.user_id
            parameters = get_assistance_parameters_by_key(
                received_assistance_object.parameters,
                ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE_RESPONSE,
            )
            peer_user_ids = list(
                filter(
                    lambda related_user_id: related_user_id != user_id, related_user_ids
                )
            )
            for parameter in parameters:
                assistance_objects += list(
                    map(
                        lambda peer_user_id: AssistanceObject.create_with_default_parameters(
                            user_id=peer_user_id,
                            parameters=[
                                AssistanceParameter.create_with_default_parameters(
                                    key=ASSISTANCE_OBJECT_PARAMETER_KEY_USER_MESSAGE,
                                    value=parameter.value,
                                )
                            ],
                        ),
                        peer_user_ids,
                    )
                )

        assistance.assistance_objects = assistance_objects
        return AssistanceResult(assistance=[assistance])


class FinishPeerExchangeOperation(AssistanceOperation):
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
                    state_update_parameter = get_first_assistance_parameter_by_key(
                        received_assistance_object.parameters, ASSISTANCE_OBJECT_PARAMETER_KEY_STATE_UPDATE_RESPONSE)
                    if state_update_parameter.value == AssistanceStateStatus.COMPLETED.value:
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
        related_user_ids = get_first_assistance_parameter_by_key(
            assistance.parameters,
            ASSISTANCE_PARAMETER_KEY_RELATED_USER_IDS,
        ).value
        parameters_to_send = [
            AssistanceParameter.create_with_default_parameters(
                key=ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE,
                value=t(LOCALE_IDENTIFIER_DE,
                        'assistance.peer_exchange.operation.system_message_exchange_finished'),
            ),
            AssistanceParameter.create_with_default_parameters(
                key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_CHAT
            ),
            AssistanceParameter.create_with_default_parameters(
                key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_ABORT_EXCHANGE_COMMAND
            ),
        ]
        assistance.assistance_objects = []
        for related_user_id in related_user_ids:
            assistance.assistance_objects += [
                AssistanceObject.create_with_default_parameters(
                    user_id=related_user_id,
                    parameters=[parameter_to_send]
                )
                for parameter_to_send in parameters_to_send]
        return AssistanceResult(assistance=[assistance])
