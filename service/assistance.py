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

import uuid
from typing import List, Dict

from dateutil import parser
from loguru import logger

from assistance.cooperative_assistance.peer_collaboration import PeerCollaborationAssistance
from assistance.cooperative_assistance.peer_exchange import PeerExchangeAssistance
from assistance.proactive_assistance.ask_for_exchange_willingness import AskForExchangeWillingnessAssistance
from assistance.reactive_assistance.debug import DebugAssistance
from assistance.reactive_assistance.entry_test_feedback import EntryTestFeedbackAssistance
from assistance.reactive_assistance.final_test_feedback import FinalTestFeedbackAssistance
from assistance.reactive_assistance.final_test_result_feedback import FinalTestResultFeedbackAssistance
from assistance.reactive_assistance.greeting import GreetingAssistance
from assistance.reactive_assistance.knowledge_structure_hint import KnowledgeStructureHintAssistance
from assistance.reactive_assistance.learning_diary_hint import LearningDiaryHintAssistance
from assistance.reactive_assistance.offer_assistance_options import OfferAssistanceOptionsAssistance
from assistance.reactive_assistance.tool_check_hint import ToolCheckHintAssistance
from error.tutorial_module import (
    AssistanceOperationException, )
from model.core.student_module import Statement, StatementVerbId, StatementSimulation
from model.core.tutorial_module import AssistanceType, AssistanceParameter, AssistanceObject, \
    AssistanceStateStatus, AssistanceObjectType
from model.service.assistance import (
    AssistanceRequest,
    AssistanceContext,
    KindOfAssistanceType,
    AssistanceResult,
    ASSISTANCE_OPERATION_KEY_INITIATION,
    ASSISTANCE_CONTEXT_PARAMETER_KEY_STATEMENT_ID, ASSISTANCE_CONTEXT_PARAMETER_KEY_A_ID,
    ASSISTANCE_CONTEXT_PARAMETER_KEY_ASSISTANCE_OBJECTS,
)
from service import full_stack
from service.administration import debug
from service.administration import read_setting_by_key, SETTING_KEY_SCHEDULED_ASSISTANCE_DISABLED
from service.backend import send_assistance
from service.datetime import current_datetime
from service.db.assistance import read_assistance_by_status, update_assistance_by_a_id_adding_assistance_objects
from service.db.assistance_operation import read_assistance_operation_by_time_of_invocation_before_date, \
    delete_assistance_operation
from service.db.statement_simulation import create_statement_simulation, \
    read_statement_simulations_by_time_of_invocation_before_date, delete_statement_simulation_by_simulation_id, \
    update_statement_simulation
from service.environment import disabled_assistance_type_keys
from service.statement import process_statement

ASSISTANCE_TYPES = {
    # AskAiForHelpAssistance.get_key(): lambda: AskAiForHelpAssistance(),
    AskForExchangeWillingnessAssistance.get_key(): lambda: AskForExchangeWillingnessAssistance(),
    EntryTestFeedbackAssistance.get_key(): lambda: EntryTestFeedbackAssistance(),
    FinalTestFeedbackAssistance.get_key(): lambda: FinalTestFeedbackAssistance(),
    FinalTestResultFeedbackAssistance.get_key(): lambda: FinalTestResultFeedbackAssistance(),
    GreetingAssistance.get_key(): lambda: GreetingAssistance(),
    KnowledgeStructureHintAssistance.get_key(): lambda: KnowledgeStructureHintAssistance(),
    LearningDiaryHintAssistance.get_key(): lambda: LearningDiaryHintAssistance(),
    OfferAssistanceOptionsAssistance.get_key(): lambda: OfferAssistanceOptionsAssistance(),
    PeerCollaborationAssistance.get_key(): lambda: PeerCollaborationAssistance(),
    PeerExchangeAssistance.get_key(): lambda: PeerExchangeAssistance(),
    ToolCheckHintAssistance.get_key(): lambda: ToolCheckHintAssistance(),
}

if debug():
    ASSISTANCE_TYPES |= {DebugAssistance.get_key(): lambda: DebugAssistance()}

COOPERATIVE_ASSISTANCE_TYPES = list(
    filter(
        lambda assistance_type: assistance_type().get_kind() == KindOfAssistanceType.COOPERATIVE_ASSISTANCE,
        ASSISTANCE_TYPES.values(),
    )
)

INFORMATIONAL_FEEDBACK_ASSISTANCE_TYPES = list(
    filter(
        lambda assistance_type: assistance_type().get_kind() == KindOfAssistanceType.INFORMATIONAL_FEEDBACK,
        ASSISTANCE_TYPES.values(),
    )
)

PROACTIVE_ASSISTANCE_TYPES = list(
    filter(
        lambda assistance_type: assistance_type().get_kind() == KindOfAssistanceType.PROACTIVE_ASSISTANCE,
        ASSISTANCE_TYPES.values(),
    )
)

REACTIVE_ASSISTANCE_TYPES = list(
    filter(
        lambda assistance_type: assistance_type().get_kind() == KindOfAssistanceType.REACTIVE_ASSISTANCE,
        ASSISTANCE_TYPES.values(),
    )
)

DISABLED_ASSISTANCE_TYPE_KEYS = disabled_assistance_type_keys()


def get_assistance_type(key: str) -> AssistanceType | None:
    return next(filter(lambda assistance_type: assistance_type.key == key, get_assistance_types()), None)


def get_assistance_types(
        kind: KindOfAssistanceType = None,
) -> List[AssistanceType]:
    match kind:
        case None:
            assistance_types = ASSISTANCE_TYPES
        case KindOfAssistanceType.COOPERATIVE_ASSISTANCE:
            assistance_types = COOPERATIVE_ASSISTANCE_TYPES
        case KindOfAssistanceType.INFORMATIONAL_FEEDBACK:
            assistance_types = INFORMATIONAL_FEEDBACK_ASSISTANCE_TYPES
        case KindOfAssistanceType.PROACTIVE_ASSISTANCE:
            assistance_types = PROACTIVE_ASSISTANCE_TYPES
        case KindOfAssistanceType.REACTIVE_ASSISTANCE:
            assistance_types = REACTIVE_ASSISTANCE_TYPES
        case _:
            raise ValueError(f"Invalid kind of feedback type '{kind}'")

    supported_assistance_type_keys = list(
        filter(
            lambda assistance_type_key: assistance_type_key not in DISABLED_ASSISTANCE_TYPE_KEYS,
            assistance_types.keys(),
        )
    )
    return list(
        map(
            lambda supported_assistance_type_key: ASSISTANCE_TYPES[
                supported_assistance_type_key
            ]().get_type(),
            supported_assistance_type_keys,
        )
    )


def get_assistance_type_keys() -> List[str]:
    return list(map(lambda assistance_type: assistance_type.key, get_assistance_types()))


def assistance_by_request(
        assistance_request: AssistanceRequest,
) -> AssistanceResult | None:
    assistance_type_key = assistance_request.assistance_type_key
    if assistance_type_key not in ASSISTANCE_TYPES:
        raise ValueError(f"Assistance type '{assistance_type_key}' not defined!")

    return __handle_assistance_request(
        assistance_request,
        list(
            map(
                lambda assistance_type: assistance_type().get_key(),
                ASSISTANCE_TYPES.values(),
            )
        ),
    )


def check_statements_to_simulate() -> None:
    now = current_datetime()
    statement_simulations = read_statement_simulations_by_time_of_invocation_before_date(now)

    if len(statement_simulations) == 0:
        return

    statements_to_simulate_by_statement_id = {}
    supported_assistance_types_by_statement_id = {}

    for statement_simulation in statement_simulations:
        statement_id = statement_simulation.next_statement.id
        logger.info(f"Simulate statement {statement_id}.")
        statements_to_simulate_by_statement_id[statement_id] = statement_simulation.next_statement
        supported_assistance_types_by_statement_id[statement_id] = statement_simulation.supported_assistance_types
        if len(statement_simulation.subsequent_statements) == 0:
            delete_statement_simulation_by_simulation_id(statement_simulation.simulation_id)
            continue

        timestamp_of_statement_to_simulate = parser.parse(statement_simulation.next_statement.timestamp)
        next_statement_to_simulate = statement_simulation.subsequent_statements[0]
        timestamp_of_next_statement_to_simulate = parser.parse(next_statement_to_simulate.timestamp)
        td_statements = timestamp_of_next_statement_to_simulate - timestamp_of_statement_to_simulate
        next_simulation_point = now + (td_statements * statement_simulation.time_factor)
        next_statement_to_simulate.timestamp = next_simulation_point.isoformat(timespec='microseconds')

        statement_simulation.next_statement = next_statement_to_simulate
        statement_simulation.subsequent_statements = statement_simulation.subsequent_statements[1:]
        statement_simulation.time_of_invocation = next_simulation_point
        update_statement_simulation(statement_simulation)

    for statement_id, statement in statements_to_simulate_by_statement_id.items():
        assistance = assistance_by_statement(statement, supported_assistance_types_by_statement_id[statement_id])
        if assistance is not None:
            send_assistance(assistance.assistance)


def assistance_by_simulation(statement_simulation: StatementSimulation) -> StatementSimulation:
    if statement_simulation.user_id is not None:
        statement_simulation.next_statement.actor.account.name = statement_simulation.user_id
        for statement in statement_simulation.subsequent_statements:
            statement.actor.account.name = statement_simulation.user_id
    statement_simulation.next_statement.id = str(uuid.uuid4())
    for statement in statement_simulation.subsequent_statements:
        statement.id = str(uuid.uuid4())
    statement_simulation.time_of_invocation = current_datetime()
    return create_statement_simulation(statement_simulation)


def assistance_by_statement(
        statement: Statement, supported_assistance_type_keys: List[str]
) -> AssistanceResult | None:
    process_statement(statement)

    if statement.verb.id == StatementVerbId.ASSISTED.value:
        return None

    relevant_assistance_type_keys = list(
        filter(
            lambda assistance_type_key: assistance_type_key in supported_assistance_type_keys,
            get_assistance_type_keys(),
        )
    )

    ctx = AssistanceContext({ASSISTANCE_CONTEXT_PARAMETER_KEY_STATEMENT_ID: statement.id})
    assistance = []

    # Check new assistance process to initiate
    for relevant_assistance_type_key in relevant_assistance_type_keys:
        try:
            assistance_result = __handle_assistance_request(
                AssistanceRequest(
                    assistance_type_key=relevant_assistance_type_key,
                    assistance_operation_key=ASSISTANCE_OPERATION_KEY_INITIATION,
                    ctx=ctx,
                ),
                supported_assistance_type_keys,
            )
        except AssistanceOperationException:
            continue
        if assistance_result is None:
            continue
        assistance += assistance_result.assistance

    # TODO: Only check assistance processes related to the user who is referenced by the statement
    # Check assistance in progress
    assistance_processes_in_progress = read_assistance_by_status(
        [AssistanceStateStatus.INITIATED, AssistanceStateStatus.IN_PROGRESS])
    for assistance_in_progress in assistance_processes_in_progress:
        # TODO: Integrate check for next operation keys in Mongo query
        if assistance_in_progress.next_operation_keys is None or len(assistance_in_progress.next_operation_keys) == 0:
            continue
        for next_operation_key in assistance_in_progress.next_operation_keys:
            try:
                assistance_result = __handle_assistance_request(
                    AssistanceRequest(
                        assistance_type_key=assistance_in_progress.type_key,
                        assistance_operation_key=next_operation_key,
                        ctx=AssistanceContext({ASSISTANCE_CONTEXT_PARAMETER_KEY_STATEMENT_ID: statement.id,
                                               ASSISTANCE_CONTEXT_PARAMETER_KEY_A_ID: assistance_in_progress.a_id}),
                    ),
                    supported_assistance_type_keys,
                )
            except AssistanceOperationException:
                continue
            if assistance_result is None:
                continue
            assistance += assistance_result.assistance

    return None if (not assistance) else AssistanceResult(assistance=assistance)


def check_scheduled_assistance_operations() -> None:
    if debug():
        scheduled_assistance_disabled = read_setting_by_key(SETTING_KEY_SCHEDULED_ASSISTANCE_DISABLED)
        if scheduled_assistance_disabled is not None and scheduled_assistance_disabled.value:
            return

    assistance_operations = read_assistance_operation_by_time_of_invocation_before_date(current_datetime())
    for assistance_operation in assistance_operations:
        try:
            result = __handle_assistance_request(
                AssistanceRequest(
                    assistance_type_key=assistance_operation.assistance_type_key,
                    assistance_operation_key=assistance_operation.assistance_operation_key,
                    ctx=assistance_operation.ctx,
                ),
                list(
                    map(
                        lambda assistance_type: assistance_type().get_key(),
                        ASSISTANCE_TYPES.values(),
                    )
                ),
            )
            if result is not None and result.assistance is not None:
                send_assistance(result.assistance)
            delete_assistance_operation(assistance_operation)
        except Exception as e:
            logger.error(
                f"An error occurred during the execution of operation {assistance_operation.assistance_operation_key} for {assistance_operation.a_id}! {full_stack()}")


def update_assistance(
        a_id: str, assistance_response_objects: List[AssistanceObject],
) -> AssistanceResult | None:
    # Store assistance objects
    for assistance_object in assistance_response_objects:
        assistance_object.type = AssistanceObjectType.ASSISTANCE_RESPONSE_OBJECT
    assistance = update_assistance_by_a_id_adding_assistance_objects(a_id, assistance_response_objects)

    # Check which further assistance has to be provided
    ctx = AssistanceContext({ASSISTANCE_CONTEXT_PARAMETER_KEY_A_ID: a_id,
                             ASSISTANCE_CONTEXT_PARAMETER_KEY_ASSISTANCE_OBJECTS: assistance_response_objects})
    assistance_update_result = []
    supported_assistance_type_keys = list(map(lambda assistance_type: assistance_type.key, get_assistance_types()))
    for next_operation_key in assistance.next_operation_keys:
        try:
            assistance_result = __handle_assistance_request(
                AssistanceRequest(
                    assistance_type_key=assistance.type_key,
                    assistance_operation_key=next_operation_key,
                    ctx=ctx,
                ),
                supported_assistance_type_keys,
            )
        except AssistanceOperationException:
            continue
        if assistance_result is None:
            continue
        assistance_update_result += assistance_result.assistance

    return None if (not assistance_update_result) else AssistanceResult(assistance=assistance_update_result)


def get_assistance_initiation_parameters_dict(
        assistance_initiation_parameters: List[AssistanceParameter],
) -> Dict:
    return {parameter.key: parameter.value for parameter in assistance_initiation_parameters}


def __handle_assistance_request(
        assistance_request: AssistanceRequest, supported_assistance_type_keys: List[str]
) -> AssistanceResult | None:
    if (
            assistance_request.assistance_type_key in DISABLED_ASSISTANCE_TYPE_KEYS
            or assistance_request.assistance_type_key not in supported_assistance_type_keys
    ):
        return None

    assistance_result = ASSISTANCE_TYPES[
        assistance_request.assistance_type_key
    ]().check_applicability_and_execute_operation(
        assistance_request.assistance_operation_key, assistance_request.ctx
    )

    if assistance_result is None:
        return None
    if not assistance_result.assistance_requests:
        return assistance_result

    logger.debug(
        f"Assistance request were generated: {', '.join([request.assistance_operation_key + '/' + request.assistance_type_key for request in assistance_result.assistance_requests])}")

    assistance = [] if assistance_result.prepend_assistance_from_requests else assistance_result.assistance
    for assistance_request in assistance_result.assistance_requests:
        assistance += __handle_assistance_request(
            assistance_request, supported_assistance_type_keys
        ).assistance
    if assistance_result.prepend_assistance_from_requests:
        assistance += assistance_result.assistance
    return AssistanceResult(assistance=assistance)
