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

from loguru import logger

from assistance import get_first_assistance_parameter_by_key, replace_or_add_assistance_parameters_by_key
from assistance.cooperative_assistance.peer_exchange import PeerExchangeAssistance
from assistance.proactive_assistance.ask_for_exchange_willingness import AskForExchangeWillingnessAssistance
from assistance.reactive_assistance import ReactiveAssistanceProcess
from error.tutorial_module import AssistanceParameterException
from model.core.expert_module import LCO_ATTRIBUTE_KEY_ENTRY_TEST_INDICATOR, LCO_ATTRIBUTE_KEY_FINAL_TEST_INDICATOR
from model.core.student_module import StatementVerbId
from model.core.tutorial_module import (
    Assistance,
    AssistanceObject,
    AssistanceParameter,
    AssistanceStateStatus,
)
from model.service.assistance import (
    AssistanceContext,
    AssistanceResult,
    ASSISTANCE_OPERATION_KEY_INITIATION,
    AssistanceOperation,
    ASSISTANCE_CONTEXT_PARAMETER_KEY_STATEMENT_ID,
    ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE, ASSISTANCE_OBJECT_PARAMETER_KEY_OPTIONS,
    ASSISTANCE_OBJECT_PARAMETER_OPTIONS_KEY_TRADITIONAL_FEEDBACK, ASSISTANCE_OBJECT_PARAMETER_OPTIONS_KEY_PEER_EXCHANGE,
    ASSISTANCE_CONTEXT_PARAMETER_KEY_ASSISTANCE_OBJECTS, ASSISTANCE_OBJECT_PARAMETER_KEY_OPTIONS_RESPONSE,
    ASSISTANCE_CONTEXT_PARAMETER_KEY_A_ID, SubsequentAssistanceOperation, SubsequentAssistanceOperationType,
    ASSISTANCE_OBJECT_PARAMETER_OPTIONS_KEY_ACCEPTED,
    ASSISTANCE_OBJECT_PARAMETER_OPTIONS_KEY_DECLINED, AssistanceRequest,
    ASSISTANCE_TYPE_PARAMETER_KEY_USER_IDS_COLLABORATORS, ASSISTANCE_TYPE_PARAMETER_KEY_USER_ID_INITIATOR,
    ASSISTANCE_PARAMETER_KEY_RELATED_USER_IDS,
    ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION, ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_OPTIONS,
    ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_OPTIONS,
    ASSISTANCE_TYPE_PARAMETER_KEY_USER_ID,
    ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE, ASSISTANCE_OPERATION_KEY_ABORTION, )
from service.db.assistance import read_assistance_by_a_id, read_assistance_by_user_id_and_type_keys_and_status, \
    read_assistance_by_related_user_id_and_type_keys_and_status
from service.db.experience import read_experiences_by_object_id_and_verb_id
from service.db.learning_content_object import read_learning_content_object_by_object_id
from service.db.statement import read_statement_by_id
from service.db.student_model import read_student_models_by_user_ids_and_online_and_cooperativeness, \
    update_student_model_cooperativeness_by_user_id
from service.i18n import t, LOCALE_IDENTIFIER_DE
from service.learning_content_object import get_learning_content_object_attribute_value
from service.statement import get_user_id


class OfferAssistanceOptionsAssistance(ReactiveAssistanceProcess):
    ASSISTANCE_OPERATION_KEY_ABORT_NO_PEER_ANSWERING = "abort_no_peer_answering"
    ASSISTANCE_OPERATION_KEY_WAIT_FOR_PEER_CONFIRMATION = "wait_for_peer_confirmation"
    ASSISTANCE_PARAMETER_KEY_COMPLETED_LCO_OBJECT_ID = "completed_lco_object_id"
    ASSISTANCE_PARAMETER_KEY_STATEMENT_RESULT = "statement_result"

    @staticmethod
    def get_key() -> str:
        return "offer_assistance_options"

    def __init__(self) -> None:
        super().__init__()

        assistance_operation_key_abort_offer_assistance_options = "abort_offer_assistance_options"
        assistance_operation_key_wait_for_option_response = "wait_for_option_response"

        self._register_operation(
            ASSISTANCE_OPERATION_KEY_INITIATION,
            OfferAssistanceOptionsAssistanceInitiationOperation(
                assistance_process=self,
                target_status=AssistanceStateStatus.IN_PROGRESS,
                subsequent_operations=[
                    SubsequentAssistanceOperation(
                        type=SubsequentAssistanceOperationType.TRIGGERED_OPERATION,
                        operation_key=assistance_operation_key_wait_for_option_response,
                    ),
                    SubsequentAssistanceOperation(
                        type=SubsequentAssistanceOperationType.SCHEDULED_OPERATION,
                        operation_key=assistance_operation_key_abort_offer_assistance_options,
                        time_to_invocation_in_s=120
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
            self.ASSISTANCE_OPERATION_KEY_WAIT_FOR_PEER_CONFIRMATION,
            WaitForPeerConfirmationOperation(
                assistance_process=self,
                target_status=AssistanceStateStatus.IN_PROGRESS,
            ),
        )
        self._register_operation(
            assistance_operation_key_abort_offer_assistance_options,
            AbortOfferAssistanceOptionsNoOptionSelectedOperation(
                assistance_process=self,
                target_status=AssistanceStateStatus.ABORTED,
                subsequent_operations=[],
                assistance_in_progress_required=True,
                delete_scheduled_operations=True,
                send_state_update_to_related_users=False
            ),
        )
        self._register_operation(
            self.ASSISTANCE_OPERATION_KEY_ABORT_NO_PEER_ANSWERING,
            AbortNoPeerAnsweringOperation(
                assistance_process=self,
                target_status=AssistanceStateStatus.ABORTED,
                subsequent_operations=[],
                assistance_in_progress_required=True,
                delete_scheduled_operations=True,
            ),
        )
        self._register_operation(
            ASSISTANCE_OPERATION_KEY_ABORTION,
            AbortOfferAssistanceOptionsOperation(
                assistance_process=self,
                target_status=AssistanceStateStatus.ABORTED,
                subsequent_operations=[],
                assistance_in_progress_required=True,
                delete_scheduled_operations=True,
            ),
        )


class OfferAssistanceOptionsAssistanceInitiationOperation(AssistanceOperation):
    def is_applicable(self, ctx: AssistanceContext) -> bool:
        try:
            statement = read_statement_by_id(
                ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_STATEMENT_ID)
            )
            if statement is None or statement.verb.id != StatementVerbId.COMPLETED.value:
                return False
            lco = read_learning_content_object_by_object_id(statement.object.id)
            if lco is None:
                return False
            entry_test_indicator_attribute_value = get_learning_content_object_attribute_value(
                lco=lco, lco_attribute_key=LCO_ATTRIBUTE_KEY_ENTRY_TEST_INDICATOR)
            if entry_test_indicator_attribute_value is not None and entry_test_indicator_attribute_value is True:
                return False
            final_test_indicator_attribute_value = get_learning_content_object_attribute_value(
                lco=lco, lco_attribute_key=LCO_ATTRIBUTE_KEY_FINAL_TEST_INDICATOR)
            if final_test_indicator_attribute_value is not None and final_test_indicator_attribute_value is True:
                return False
        except (AssistanceParameterException | AttributeError):
            return False
        return True

    def _execute(self, ctx: AssistanceContext) -> AssistanceResult | None:
        statement_id = ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_STATEMENT_ID)
        statement = read_statement_by_id(statement_id)
        user_id = get_user_id(statement)

        # Abort assistance processes in progress of type offer_assistance_options for the user
        assistance_in_progress = read_assistance_by_user_id_and_type_keys_and_status(
            user_id=user_id, type_keys=[OfferAssistanceOptionsAssistance.get_key()],
            possible_states=[AssistanceStateStatus.IN_PROGRESS])
        assistance_requests = [
            AssistanceRequest(
                assistance_type_key=OfferAssistanceOptionsAssistance.get_key(),
                assistance_operation_key=ASSISTANCE_OPERATION_KEY_ABORTION,
                ctx=AssistanceContext(
                    {
                        ASSISTANCE_CONTEXT_PARAMETER_KEY_A_ID: assistance.a_id
                    })
            ) for assistance in assistance_in_progress
        ]

        potential_peers_user_ids = list(filter(lambda u_id: u_id != user_id, [
            student_model.user_id for student_model in
            read_student_models_by_user_ids_and_online_and_cooperativeness(
                user_ids=[experience.user_id for experience in
                          read_experiences_by_object_id_and_verb_id(
                              statement.object.id, StatementVerbId.COMPLETED.value)],
                online=True, cooperativeness=True)]))
        logger.debug(f"Found {len(potential_peers_user_ids)} potential peers: {', '.join(potential_peers_user_ids)}")
        # Filter out users who are involved in an assistance process or were requested for an exchange
        potential_peers_user_ids = list(filter(lambda u_id: len(
            read_assistance_by_related_user_id_and_type_keys_and_status(user_id=u_id, type_keys=[
                OfferAssistanceOptionsAssistance.get_key(), PeerExchangeAssistance.get_key()], possible_states=[
                AssistanceStateStatus.INITIATED, AssistanceStateStatus.IN_PROGRESS])) == 0,
                                               potential_peers_user_ids))
        logger.debug(
            f"After filter out peers that were requested or are involved {len(potential_peers_user_ids)} potential peers are left: {', '.join(potential_peers_user_ids)}")
        # Filter out users who are requesting other users or were asked if they should be requested
        potential_peers_user_ids = list(filter(lambda u_id: len(
            read_assistance_by_user_id_and_type_keys_and_status(user_id=u_id, type_keys=[
                OfferAssistanceOptionsAssistance.get_key(), AskForExchangeWillingnessAssistance.get_key()],
                                                                possible_states=[
                                                                    AssistanceStateStatus.INITIATED,
                                                                    AssistanceStateStatus.IN_PROGRESS])) == 0,
                                               potential_peers_user_ids))
        logger.debug(
            f"After filter out peers that requested on their own {len(potential_peers_user_ids)} potential peers are left: {', '.join(potential_peers_user_ids)}")

        success = statement.result.score.scaled == 1.0

        if len(potential_peers_user_ids) == 0:
            self.subsequent_operations = []
            self.target_status = AssistanceStateStatus.COMPLETED
            return AssistanceResult(assistance=[Assistance.create_with_default_parameters(
                user_id=user_id,
                assistance_objects=[
                    AssistanceObject.create_with_default_parameters(
                        user_id=user_id,
                        parameters=[
                            AssistanceParameter.create_with_default_parameters(
                                key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                                value=t(
                                    LOCALE_IDENTIFIER_DE,
                                    "assistance.offer_assistance_options.operation.message_task_completed_successfully" if success else "assistance.offer_assistance_options.operation.message_task_completed_not_successfully",
                                ),
                            ),
                        ],
                    )
                ],
            )], assistance_requests=assistance_requests, prepend_assistance_from_requests=True)

        assistance = Assistance.create_with_default_parameters(
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
                                "assistance.offer_assistance_options.operation.message_offer_assistance_options",
                            ),
                        ),
                        AssistanceParameter.create_with_default_parameters(
                            key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPTIONS,
                            value=[
                                AssistanceParameter.create_with_default_parameters(
                                    key=ASSISTANCE_OBJECT_PARAMETER_OPTIONS_KEY_TRADITIONAL_FEEDBACK,
                                    value=t(
                                        LOCALE_IDENTIFIER_DE,
                                        "assistance.offer_assistance_options.operation.message_offer_option_traditional_feedback",
                                    ),
                                ),
                                AssistanceParameter.create_with_default_parameters(
                                    key=ASSISTANCE_OBJECT_PARAMETER_OPTIONS_KEY_PEER_EXCHANGE,
                                    value=t(
                                        LOCALE_IDENTIFIER_DE,
                                        "assistance.offer_assistance_options.operation.message_offer_option_peer_exchange",
                                    ),
                                ),
                            ],
                        )
                    ],
                )
            ],
        )

        assistance.parameters = [
            AssistanceParameter.create_with_default_parameters(
                OfferAssistanceOptionsAssistance.ASSISTANCE_PARAMETER_KEY_COMPLETED_LCO_OBJECT_ID,
                statement.object.id,
            ),
            AssistanceParameter.create_with_default_parameters(
                OfferAssistanceOptionsAssistance.ASSISTANCE_PARAMETER_KEY_STATEMENT_RESULT,
                statement.result,
            ),
        ]

        return AssistanceResult(
            assistance=[assistance], assistance_requests=assistance_requests, prepend_assistance_from_requests=True)


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

        if provided_object_value == ASSISTANCE_OBJECT_PARAMETER_OPTIONS_KEY_TRADITIONAL_FEEDBACK:
            success = get_first_assistance_parameter_by_key(
                assistance.parameters,
                OfferAssistanceOptionsAssistance.ASSISTANCE_PARAMETER_KEY_STATEMENT_RESULT,
            ).value.score.scaled == 1.0

            self.delete_scheduled_operations = True
            self.subsequent_operations = []
            self.prevent_progress = False
            self.target_status = AssistanceStateStatus.COMPLETED
            assistance.assistance_objects = [
                AssistanceObject.create_with_default_parameters(
                    user_id=assistance.user_id,
                    parameters=[
                        AssistanceParameter.create_with_default_parameters(
                            key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                            value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_OPTIONS
                        ),
                    ]
                ),
                AssistanceObject.create_with_default_parameters(
                    user_id=assistance.user_id,
                    parameters=[
                        AssistanceParameter.create_with_default_parameters(
                            key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                            value=t(
                                LOCALE_IDENTIFIER_DE,
                                "assistance.offer_assistance_options.operation.message_task_completed_successfully" if success else "assistance.offer_assistance_options.operation.message_task_completed_not_successfully",
                            ),
                        ),
                    ]
                )
            ]
            return AssistanceResult(assistance=[assistance])
        elif provided_object_value == ASSISTANCE_OBJECT_PARAMETER_OPTIONS_KEY_PEER_EXCHANGE:
            update_student_model_cooperativeness_by_user_id(user_id=assistance.user_id, cooperativeness=True)
            self.delete_scheduled_operations = True
            self.prevent_progress = False

            assistance_in_progress = read_assistance_by_user_id_and_type_keys_and_status(
                user_id=assistance.user_id, type_keys=[PeerExchangeAssistance.get_key()],
                possible_states=[AssistanceStateStatus.IN_PROGRESS])
            assistance_requests = [
                AssistanceRequest(
                    assistance_type_key=PeerExchangeAssistance.get_key(),
                    assistance_operation_key=ASSISTANCE_OPERATION_KEY_ABORTION,
                    ctx=AssistanceContext(
                        {
                            ASSISTANCE_CONTEXT_PARAMETER_KEY_A_ID: peer_exchange_assistance.a_id
                        })
                ) for peer_exchange_assistance in assistance_in_progress
            ]

            object_id = get_first_assistance_parameter_by_key(
                assistance.parameters,
                OfferAssistanceOptionsAssistance.ASSISTANCE_PARAMETER_KEY_COMPLETED_LCO_OBJECT_ID,
            ).value
            related_user_ids = list(filter(lambda u_id: u_id != assistance.user_id, [
                student_model.user_id for student_model in
                read_student_models_by_user_ids_and_online_and_cooperativeness(
                    user_ids=[experience.user_id for experience in
                              read_experiences_by_object_id_and_verb_id(
                                  object_id, StatementVerbId.COMPLETED.value)],
                    online=True, cooperativeness=True)]))
            logger.debug(
                f"Found {len(related_user_ids)} potential peers: {', '.join(related_user_ids)}")
            # Filter out users who are involved in an assistance process or were requested for an exchange
            related_user_ids = list(filter(lambda u_id: len(
                read_assistance_by_related_user_id_and_type_keys_and_status(user_id=u_id, type_keys=[
                    OfferAssistanceOptionsAssistance.get_key(), PeerExchangeAssistance.get_key()], possible_states=[
                    AssistanceStateStatus.INITIATED, AssistanceStateStatus.IN_PROGRESS])) == 0,
                                           related_user_ids))
            logger.debug(
                f"After filter out peers that were requested or are involved {len(related_user_ids)} potential peers are left: {', '.join(related_user_ids)}")
            # Filter out users who are requesting other users or were asked if they should be requested
            related_user_ids = list(filter(lambda u_id: len(
                read_assistance_by_user_id_and_type_keys_and_status(user_id=u_id, type_keys=[
                    OfferAssistanceOptionsAssistance.get_key(), AskForExchangeWillingnessAssistance.get_key()],
                                                                    possible_states=[
                                                                        AssistanceStateStatus.INITIATED,
                                                                        AssistanceStateStatus.IN_PROGRESS])) == 0,
                                           related_user_ids))[:4]
            logger.debug(
                f"After filter out peers that requested on their own {len(related_user_ids)} potential peers are left: {', '.join(related_user_ids)}")

            if len(related_user_ids) == 0:
                self.subsequent_operations = []
                self.target_status = AssistanceStateStatus.COMPLETED
                assistance.assistance_objects = [
                    AssistanceObject.create_with_default_parameters(
                        user_id=assistance.user_id,
                        parameters=[
                            AssistanceParameter.create_with_default_parameters(
                                key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                                value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_OPTIONS
                            ),
                        ]
                    ),
                    AssistanceObject.create_with_default_parameters(
                        user_id=assistance.user_id,
                        parameters=[
                            AssistanceParameter.create_with_default_parameters(
                                key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                                value=t(LOCALE_IDENTIFIER_DE,
                                        'assistance.offer_assistance_options.operation.message_different_peer_selected'),
                            ),
                        ],
                    )
                ]
                return AssistanceResult(assistance=[assistance],
                                        assistance_requests=assistance_requests, prepend_assistance_from_requests=True)

            self.subsequent_operations = [
                SubsequentAssistanceOperation(
                    type=SubsequentAssistanceOperationType.TRIGGERED_OPERATION,
                    operation_key=OfferAssistanceOptionsAssistance.ASSISTANCE_OPERATION_KEY_WAIT_FOR_PEER_CONFIRMATION,
                ),
                SubsequentAssistanceOperation(
                    type=SubsequentAssistanceOperationType.SCHEDULED_OPERATION,
                    operation_key=OfferAssistanceOptionsAssistance.ASSISTANCE_OPERATION_KEY_ABORT_NO_PEER_ANSWERING,
                    time_to_invocation_in_s=120
                )
            ]

            assistance.assistance_objects = []
            for related_user_id in related_user_ids:
                assistance.assistance_objects += [
                    AssistanceObject.create_with_default_parameters(
                        user_id=related_user_id,
                        parameters=[
                            AssistanceParameter.create_with_default_parameters(
                                key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                                value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_OPTIONS,
                            ),
                        ]
                    ),
                    AssistanceObject.create_with_default_parameters(
                        user_id=related_user_id,
                        parameters=[
                            AssistanceParameter.create_with_default_parameters(
                                key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                                value=t(LOCALE_IDENTIFIER_DE,
                                        'assistance.offer_assistance_options.operation.message_peer_would_like_to_connect'),
                            ),
                            AssistanceParameter.create_with_default_parameters(
                                key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPTIONS,
                                value=[
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_OPTIONS_KEY_ACCEPTED,
                                        value=t(
                                            LOCALE_IDENTIFIER_DE,
                                            "assistance.offer_assistance_options.operation.option_accepted",
                                        ),
                                    ),
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_OPTIONS_KEY_DECLINED,
                                        value=t(
                                            LOCALE_IDENTIFIER_DE,
                                            "assistance.offer_assistance_options.operation.option_declined",
                                        ),
                                    ),
                                ],
                            ),
                        ]
                    ),
                ]
            assistance.assistance_objects += [
                AssistanceObject.create_with_default_parameters(
                    user_id=assistance.user_id,
                    parameters=[
                        AssistanceParameter.create_with_default_parameters(
                            key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                            value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_OPTIONS
                        ),
                    ]
                ),
                AssistanceObject.create_with_default_parameters(
                    user_id=assistance.user_id,
                    parameters=[
                        AssistanceParameter.create_with_default_parameters(
                            key=ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE,
                            value=t(LOCALE_IDENTIFIER_DE,
                                    'assistance.offer_assistance_options.operation.message_searching_for_peer'),
                        ),
                    ]
                )
            ]
            assistance.parameters.append(AssistanceParameter.create_with_default_parameters(
                ASSISTANCE_PARAMETER_KEY_RELATED_USER_IDS,
                related_user_ids,
            ))
            return AssistanceResult(
                assistance=[assistance], assistance_requests=assistance_requests, prepend_assistance_from_requests=True)
        else:
            logger.warning(f"Received unknown options response {provided_object_value}")
            self.prevent_progress = True
            return None


class WaitForPeerConfirmationOperation(AssistanceOperation):
    ASSISTANCE_PARAMETER_KEY_RELATED_USER_IDS_THAT_DECLINED_EXCHANGE = "related_user_ids_that_declined_exchange"

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
                    # TODO: Do we have to ensure that this object is sent by the right user?
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
        assistance_object = None
        for received_assistance_object in received_assistance_objects:
            try:
                provided_object_value = get_first_assistance_parameter_by_key(
                    received_assistance_object.parameters,
                    ASSISTANCE_OBJECT_PARAMETER_KEY_OPTIONS_RESPONSE).value
                assistance_object = received_assistance_object
                break
            except AssistanceParameterException:
                pass
        if provided_object_value is None:
            return None
        related_user_ids = get_first_assistance_parameter_by_key(
            assistance.parameters,
            ASSISTANCE_PARAMETER_KEY_RELATED_USER_IDS,
        ).value

        if provided_object_value == ASSISTANCE_OBJECT_PARAMETER_OPTIONS_KEY_ACCEPTED:
            self.delete_scheduled_operations = True
            self.subsequent_operations = []
            self.prevent_progress = False
            self.target_status = AssistanceStateStatus.COMPLETED
            assistance.assistance_objects = []
            for related_user_id in related_user_ids:
                assistance.assistance_objects.append(
                    AssistanceObject.create_with_default_parameters(
                        user_id=related_user_id,
                        parameters=[
                            AssistanceParameter.create_with_default_parameters(
                                key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                                value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_OPTIONS,
                            ),
                        ]
                    )
                )
                if related_user_id == assistance_object.user_id:
                    continue
                assistance.assistance_objects.append(
                    AssistanceObject.create_with_default_parameters(
                        user_id=related_user_id,
                        parameters=[
                            AssistanceParameter.create_with_default_parameters(
                                key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                                value=t(LOCALE_IDENTIFIER_DE,
                                        'assistance.offer_assistance_options.operation.message_different_peer_selected'),
                            )
                        ]
                    )
                )
            return AssistanceResult(assistance=[assistance], assistance_requests=[
                AssistanceRequest(
                    assistance_type_key=PeerExchangeAssistance.get_key(),
                    assistance_operation_key=ASSISTANCE_OPERATION_KEY_INITIATION,
                    ctx=AssistanceContext(
                        {
                            ASSISTANCE_TYPE_PARAMETER_KEY_USER_ID_INITIATOR: assistance.user_id,
                            ASSISTANCE_TYPE_PARAMETER_KEY_USER_IDS_COLLABORATORS: [
                                assistance.user_id, assistance_object.user_id]
                        })
                )
            ])
        elif provided_object_value == ASSISTANCE_OBJECT_PARAMETER_OPTIONS_KEY_DECLINED:
            try:
                related_user_ids_that_declined_exchange = get_first_assistance_parameter_by_key(
                    assistance.parameters,
                    self.ASSISTANCE_PARAMETER_KEY_RELATED_USER_IDS_THAT_DECLINED_EXCHANGE,
                ).value
            except AssistanceParameterException:
                related_user_ids_that_declined_exchange = []
            related_user_ids_that_declined_exchange.append(assistance_object.user_id)

            assistance.parameters = replace_or_add_assistance_parameters_by_key(
                AssistanceParameter.create_with_default_parameters(
                    self.ASSISTANCE_PARAMETER_KEY_RELATED_USER_IDS_THAT_DECLINED_EXCHANGE,
                    related_user_ids_that_declined_exchange,
                ), assistance.parameters
            )

            for related_user_id_that_declined_exchange in [u_id for u_id in related_user_ids_that_declined_exchange if
                                                           u_id in related_user_ids]:
                related_user_ids.remove(related_user_id_that_declined_exchange)

            assistance.assistance_objects = []
            if len(related_user_ids) == 0:
                self.delete_scheduled_operations = True
                self.subsequent_operations = []
                self.prevent_progress = False
                self.target_status = AssistanceStateStatus.ABORTED
                assistance.assistance_objects.append(
                    AssistanceObject.create_with_default_parameters(
                        user_id=assistance.user_id,
                        parameters=[
                            AssistanceParameter.create_with_default_parameters(
                                key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                                value=t(LOCALE_IDENTIFIER_DE,
                                        'assistance.offer_assistance_options.operation.message_no_peer_available'),
                            )
                        ]
                    )
                )
            else:
                self.prevent_progress = True
            assistance.assistance_objects.append(
                AssistanceObject.create_with_default_parameters(
                    user_id=assistance.user_id,
                    parameters=[
                        AssistanceParameter.create_with_default_parameters(
                            key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                            value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_OPTIONS,
                        )
                    ]
                ),
            )
            return AssistanceResult(assistance=[assistance], assistance_requests=[
                AssistanceRequest(
                    assistance_type_key=AskForExchangeWillingnessAssistance.get_key(),
                    assistance_operation_key=ASSISTANCE_OPERATION_KEY_INITIATION,
                    ctx=AssistanceContext(
                        {
                            ASSISTANCE_TYPE_PARAMETER_KEY_USER_ID: assistance_object.user_id,
                        })
                )
            ])
        else:
            self.prevent_progress = True
            logger.warning(f"Received unknown options response {provided_object_value}")
            return None


class AbortOfferAssistanceOptionsOperation(AssistanceOperation):
    def _execute(self, ctx: AssistanceContext) -> AssistanceResult | None:
        assistance = read_assistance_by_a_id(
            ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_A_ID)
        )

        assistance.assistance_objects = [AssistanceObject.create_with_default_parameters(
            user_id=assistance.user_id,
            parameters=[
                AssistanceParameter.create_with_default_parameters(
                    key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                    value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_OPTIONS,
                ),
            ]
        )]
        if assistance.assistance_state.step == ASSISTANCE_OPERATION_KEY_INITIATION:
            return AssistanceResult(assistance=[assistance])

        try:
            related_user_ids = get_first_assistance_parameter_by_key(
                assistance.parameters,
                ASSISTANCE_PARAMETER_KEY_RELATED_USER_IDS,
            ).value
        except AssistanceParameterException:
            related_user_ids = []

        for related_user_id in related_user_ids:
            assistance.assistance_objects += [
                AssistanceObject.create_with_default_parameters(
                    user_id=related_user_id,
                    parameters=[
                        AssistanceParameter.create_with_default_parameters(
                            key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                            value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_OPTIONS,
                        ),
                    ]
                ),
                AssistanceObject.create_with_default_parameters(
                    user_id=related_user_id,
                    parameters=[
                        AssistanceParameter.create_with_default_parameters(
                            key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                            value=t(LOCALE_IDENTIFIER_DE,
                                    'assistance.offer_assistance_options.operation.message_different_peer_selected'),
                        ),
                    ]
                ),
            ]
        return AssistanceResult(assistance=[assistance])


class AbortOfferAssistanceOptionsNoOptionSelectedOperation(AssistanceOperation):
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
                        value=t(LOCALE_IDENTIFIER_DE,
                                'assistance.offer_assistance_options.operation.system_message_no_feedback_option_selected'),
                    )
                ]
            )
        ]
        return AssistanceResult(assistance=[assistance])


class AbortNoPeerAnsweringOperation(AssistanceOperation):
    def _execute(self, ctx: AssistanceContext) -> AssistanceResult | None:
        assistance = read_assistance_by_a_id(
            ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_A_ID)
        )
        related_user_ids = get_first_assistance_parameter_by_key(
            assistance.parameters,
            ASSISTANCE_PARAMETER_KEY_RELATED_USER_IDS,
        ).value
        assistance.assistance_objects = []
        for related_user_id in related_user_ids:
            assistance.assistance_objects.append(AssistanceObject.create_with_default_parameters(
                user_id=related_user_id,
                parameters=[
                    AssistanceParameter.create_with_default_parameters(
                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_OPTIONS,
                    ),
                ]
            ))
            assistance.assistance_objects.append(AssistanceObject.create_with_default_parameters(
                user_id=related_user_id,
                parameters=[
                    AssistanceParameter.create_with_default_parameters(
                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                        value=t(LOCALE_IDENTIFIER_DE,
                                'assistance.offer_assistance_options.operation.message_different_peer_selected'),
                    ),
                ]
            ))
        assistance.assistance_objects.append(AssistanceObject.create_with_default_parameters(
            user_id=assistance.user_id,
            parameters=[
                AssistanceParameter.create_with_default_parameters(
                    key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                    value=t(LOCALE_IDENTIFIER_DE,
                            'assistance.offer_assistance_options.operation.message_no_peer_available'),
                )
            ]
        ))
        return AssistanceResult(assistance=[assistance])
