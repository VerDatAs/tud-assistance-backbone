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

from fibonacci import fibonacci
from loguru import logger

from assistance import (
    get_first_assistance_parameter_by_key,
    get_assistance_parameters_by_key, get_assistance_parameters_by_keys, replace_or_add_assistance_parameters_by_key,
)
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
    ASSISTANCE_OPERATION_PARAMETER_KEY_TITLE,
    AssistancePhase,
    AssistancePhaseStep,
    ASSISTANCE_OPERATION_KEY_INITIATION,
    AssistanceOperationSchedule,
    SubsequentAssistanceOperationType,
    SubsequentAssistanceOperation,
    ASSISTANCE_CONTEXT_PARAMETER_KEY_ASSISTANCE_OBJECTS,
    ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE_RESPONSE,
    ASSISTANCE_PARAMETER_KEY_RELATED_USER_IDS, ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
    ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE, ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
    ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_CHAT,
    ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_CHAT,
    ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_NOTES,
    ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_NOTES_COMMAND, ASSISTANCE_OBJECT_PARAMETER_KEY_SOLUTION_RESPONSE,
    ASSISTANCE_OBJECT_PARAMETER_KEY_USER_MESSAGE, ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_SEND_SOLUTION,
    ASSISTANCE_OBJECT_PARAMETER_KEY_PEER_SOLUTION, ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_PEER_SOLUTION,
    ASSISTANCE_PARAMETER_KEY_USER_ID_TO_STATE, ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_NOTES_COMMAND,
    ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_PEER_SOLUTION_COMMAND,
    ASSISTANCE_OBJECT_PARAMETER_KEY_SOLUTION_TEMPLATE,
    ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_PEER_SOLUTION_COMMAND,
    ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_PEER_SOLUTION,
    ASSISTANCE_OBJECT_PARAMETER_KEY_STATE_UPDATE_RESPONSE,
    ASSISTANCE_OBJECT_PARAMETER_VALUE_STATE_UPDATE_RESPONSE_STANDBY,
    ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_NOTES,
    ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_NOTES_INPUT,
    ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_NOTES_INPUT, ASSISTANCE_OBJECT_PARAMETER_KEY_RELATED_USERS,
    ASSISTANCE_OBJECT_PARAMETER_KEY_USER_ID, ASSISTANCE_OBJECT_PARAMETER_KEY_URI,
    ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_RESET_NOTES,
)
from service.db.assistance import read_assistance_by_a_id
from service.i18n import LOCALE_IDENTIFIER_DE, t


class PeerCollaborationAssistance(CooperativeAssistanceProcess):
    ASSISTANCE_OPERATION_PARAMETER_KEY_EXPECTED_OBJECT_VALUE = "expected_object_value"
    ASSISTANCE_OPERATION_PARAMETER_KEY_OBJECT_KEY_TO_WAIT_FOR = "object_key_to_wait_for"
    ASSISTANCE_OPERATION_PARAMETER_KEY_RECEIVED_OBJECTS_PARAMETER_KEY = "solutions_parameter_key"
    ASSISTANCE_OPERATION_PARAMETER_VALUE_USER_ID_TO_FINAL_SOLUTION = "final_solutions"
    ASSISTANCE_OPERATION_PARAMETER_VALUE_USER_ID_TO_READ_SOLUTION_PROGRESS = "read_solution_progress"
    ASSISTANCE_OPERATION_PARAMETER_VALUE_USER_ID_TO_SOLUTION = "solutions"
    ASSISTANCE_TYPE_PARAMETER_KEY_USER_IDS_COLLABORATORS = "collaborators"
    ASSISTANCE_TYPE_PARAMETER_KEY_USER_ID_INITIATOR = "initiator"

    @staticmethod
    def get_key() -> str:
        return "peer_collaboration"

    @staticmethod
    def get_parameters() -> List[AssistanceParameter] | None:
        return [
            AssistanceParameter.create_with_default_definition_parameters(
                key=PeerCollaborationAssistance.ASSISTANCE_TYPE_PARAMETER_KEY_USER_ID_INITIATOR,
                type=AssistanceParameterType.STRING,
                required=True,
            ),
            AssistanceParameter.create_with_default_definition_parameters(
                key=PeerCollaborationAssistance.ASSISTANCE_TYPE_PARAMETER_KEY_USER_IDS_COLLABORATORS,
                type=AssistanceParameterType.OBJECT,
                required=True,
            ),
        ]

    def __init__(self) -> None:
        super().__init__()

        assistance_operation_key_forward_message_to_peer = "forward_message_to_peer"

        self._register_operation(
            assistance_operation_key_forward_message_to_peer,
            PeerCollaborationAssistanceForwardMessageToPeerOperation(assistance_process=self, prevent_progress=True),
        )

        local_identifier = LOCALE_IDENTIFIER_DE
        self._register_phases(
            [
                AssistancePhase(
                    parameters=[
                        AssistanceParameter.create_with_default_parameters(
                            ASSISTANCE_OPERATION_PARAMETER_KEY_TITLE,
                            t(
                                local_identifier,
                                "assistance.peer_collaboration.phase.title_task_description",
                            ),
                        )
                    ],
                    steps=[
                        AssistancePhaseStep(
                            operation_key=ASSISTANCE_OPERATION_KEY_INITIATION,
                            parameters=[],
                            operation=PeerCollaborationAssistanceInitiationOperation(
                                assistance_process=self,
                                target_status=AssistanceStateStatus.IN_PROGRESS,
                            ),
                        ),
                        AssistancePhaseStep(
                            operation_key="task_description_step_2",
                            parameters=[],
                            operation=PeerCollaborationAssistanceSendObjectsToUsersOperation(
                                assistance_process=self,
                                target_status=AssistanceStateStatus.IN_PROGRESS,
                                parameters=[
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE,
                                        value=t(
                                            LOCALE_IDENTIFIER_DE,
                                            "assistance.peer_collaboration.operation.system_message_searching_for_peer",
                                        ),
                                    ),
                                ],
                            ),
                            schedule=AssistanceOperationSchedule(
                                time_to_invocation_in_s=80
                            ),
                        ),
                        AssistancePhaseStep(
                            operation_key="task_description_step_3",
                            parameters=[],
                            operation=PeerCollaborationAssistanceSendGroupFormationResultToPeersOperation(
                                assistance_process=self,
                                target_status=AssistanceStateStatus.IN_PROGRESS,
                            ),
                            schedule=AssistanceOperationSchedule(
                                time_to_invocation_in_s=10
                            ),
                        ),
                    ],
                ),
                AssistancePhase(
                    parameters=[
                        AssistanceParameter.create_with_default_parameters(
                            ASSISTANCE_OPERATION_PARAMETER_KEY_TITLE,
                            t(
                                local_identifier,
                                "assistance.peer_collaboration.phase.title_introduction",
                            ),
                        )
                    ],
                    steps=[
                        AssistancePhaseStep(
                            operation_key="introduction_step_1",
                            parameters=[],
                            operation=PeerCollaborationAssistanceSendObjectsToUsersOperation(
                                assistance_process=self,
                                target_status=AssistanceStateStatus.IN_PROGRESS,
                                parameters=[
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                                        value=t(
                                            LOCALE_IDENTIFIER_DE,
                                            "assistance.peer_collaboration.operation.message_task_description_peer_introduction",
                                        ),
                                    ),
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE,
                                        value=t(
                                            LOCALE_IDENTIFIER_DE,
                                            "assistance.peer_collaboration.operation.system_message_information_time_for_introduction_questions",
                                        ),
                                    ),
                                ],
                            ),
                            schedule=AssistanceOperationSchedule(
                                time_to_invocation_in_s=5
                            ),
                        ),
                        AssistancePhaseStep(
                            operation_key="introduction_step_2",
                            parameters=[],
                            operation=PeerCollaborationAssistanceSendObjectsToUsersOperation(
                                assistance_process=self,
                                target_status=AssistanceStateStatus.IN_PROGRESS,
                                parameters=[
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                                        value=t(
                                            LOCALE_IDENTIFIER_DE,
                                            "assistance.peer_collaboration.operation.message_task_peer_introduction",
                                        ),
                                    ),
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_CHAT,
                                    )
                                ],
                                subsequent_operations=[
                                    SubsequentAssistanceOperation(
                                        type=SubsequentAssistanceOperationType.TRIGGERED_OPERATION,
                                        operation_key=assistance_operation_key_forward_message_to_peer,
                                    )
                                ],
                            ),
                            schedule=AssistanceOperationSchedule(
                                time_to_invocation_in_s=5
                            ),
                        ),
                        AssistancePhaseStep(
                            operation_key="introduction_step_3",
                            parameters=[],
                            operation=PeerCollaborationAssistanceSendObjectsToUsersOperation(
                                assistance_process=self,
                                target_status=AssistanceStateStatus.IN_PROGRESS,
                                parameters=[
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                                        value=t(
                                            LOCALE_IDENTIFIER_DE,
                                            "assistance.peer_collaboration.operation.message_task_prior_knowledge_rating",
                                        ),
                                    ),
                                ],
                                subsequent_operations=[
                                    SubsequentAssistanceOperation(
                                        type=SubsequentAssistanceOperationType.TRIGGERED_OPERATION,
                                        operation_key=assistance_operation_key_forward_message_to_peer,
                                    )
                                ],
                            ),
                            schedule=AssistanceOperationSchedule(
                                time_to_invocation_in_s=80
                            ),
                        ),
                        AssistancePhaseStep(
                            operation_key="introduction_step_4",
                            parameters=[],
                            operation=PeerCollaborationAssistanceSendObjectsToUsersOperation(
                                assistance_process=self,
                                target_status=AssistanceStateStatus.IN_PROGRESS,
                                parameters=[
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE,
                                        value=t(
                                            LOCALE_IDENTIFIER_DE,
                                            "assistance.peer_collaboration.operation.system_message_prior_knowledge_rating_template",
                                        ),
                                    ),
                                ],
                                subsequent_operations=[
                                    SubsequentAssistanceOperation(
                                        type=SubsequentAssistanceOperationType.TRIGGERED_OPERATION,
                                        operation_key=assistance_operation_key_forward_message_to_peer,
                                    )
                                ],
                            ),
                            schedule=AssistanceOperationSchedule(
                                time_to_invocation_in_s=5
                            ),
                        ),
                    ],
                ),
                AssistancePhase(
                    parameters=[
                        AssistanceParameter.create_with_default_parameters(
                            ASSISTANCE_OPERATION_PARAMETER_KEY_TITLE,
                            t(
                                local_identifier,
                                "assistance.peer_collaboration.phase.title_individual_solution_development",
                            ),
                        )
                    ],
                    steps=[
                        AssistancePhaseStep(
                            operation_key="individual_solution_development_step_1",
                            parameters=[],
                            operation=PeerCollaborationAssistanceSendGroupInformationOperation(
                                assistance_process=self,
                                target_status=AssistanceStateStatus.IN_PROGRESS,
                                subsequent_operations=[]
                            ),
                            schedule=AssistanceOperationSchedule(
                                time_to_invocation_in_s=80
                            ),
                        ),
                        AssistancePhaseStep(
                            operation_key="individual_solution_development_step_2",
                            parameters=[],
                            operation=PeerCollaborationAssistanceSendObjectsToUsersOperation(
                                assistance_process=self,
                                target_status=AssistanceStateStatus.IN_PROGRESS,
                                parameters=[
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                                        value=t(
                                            LOCALE_IDENTIFIER_DE,
                                            "assistance.peer_collaboration.operation.message_task_description_individual_solution_development",
                                        ),
                                    ),
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE,
                                        value=t(
                                            LOCALE_IDENTIFIER_DE,
                                            "assistance.peer_collaboration.operation.system_message_information_time_for_individual_solution_development_and_exchange_and_solution_provision_part1",
                                        ),
                                    ),
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE,
                                        value=t(
                                            LOCALE_IDENTIFIER_DE,
                                            "assistance.peer_collaboration.operation.system_message_information_time_for_individual_solution_development_and_exchange_and_solution_provision_part2",
                                        ),
                                    ),
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_SOLUTION_TEMPLATE,
                                        value=t(
                                            LOCALE_IDENTIFIER_DE,
                                            "assistance.peer_collaboration.operation.solution_template",
                                        ),
                                    ),
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_CHAT,
                                    ),
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_NOTES,
                                    ),
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_NOTES_INPUT,
                                    ),
                                ],
                            ),
                            schedule=AssistanceOperationSchedule(
                                time_to_invocation_in_s=2
                            ),
                        ),
                        AssistancePhaseStep(
                            operation_key="individual_solution_development_step_3",
                            parameters=[],
                            operation=PeerCollaborationAssistanceSendObjectsToUsersOperation(
                                assistance_process=self,
                                target_status=AssistanceStateStatus.IN_PROGRESS,
                                parameters=[
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_NOTES_COMMAND,
                                    ),
                                ],
                                subsequent_operations=[SubsequentAssistanceOperation(
                                    type=SubsequentAssistanceOperationType.TRIGGERED_OPERATION,
                                    operation_key="individual_solution_development_step_6",
                                )],
                            ),
                            schedule=AssistanceOperationSchedule(
                                time_to_invocation_in_s=60 * 5
                            ),
                        ),
                        AssistancePhaseStep(
                            operation_key="individual_solution_development_step_4",
                            parameters=[],
                            operation=PeerCollaborationAssistanceSendObjectsToUsersOperation(
                                assistance_process=self,
                                target_status=AssistanceStateStatus.IN_PROGRESS,
                                parameters=[
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE,
                                        value=t(
                                            LOCALE_IDENTIFIER_DE,
                                            "assistance.peer_collaboration.operation.system_message_information_time_left_for_individual_solution_development",
                                        ),
                                    )
                                ],
                                subsequent_operations=[SubsequentAssistanceOperation(
                                    type=SubsequentAssistanceOperationType.TRIGGERED_OPERATION,
                                    operation_key="individual_solution_development_step_6",
                                )],
                            ),
                            schedule=AssistanceOperationSchedule(
                                time_to_invocation_in_s=60 * 13
                            ),
                        ),
                        AssistancePhaseStep(
                            operation_key="individual_solution_development_step_5",
                            parameters=[],
                            operation=PeerCollaborationAssistanceRequestSolutionOperation(
                                assistance_process=self,
                                target_status=AssistanceStateStatus.IN_PROGRESS,
                                subsequent_operations=[SubsequentAssistanceOperation(
                                    type=SubsequentAssistanceOperationType.SCHEDULED_OPERATION,
                                    operation_key="individual_solution_development_step_5",
                                    time_to_invocation_in_s=2
                                )]
                            ),
                            schedule=AssistanceOperationSchedule(
                                time_to_invocation_in_s=60 * 2
                            ),
                        ),
                        AssistancePhaseStep(
                            operation_key="individual_solution_development_step_6",
                            parameters=[],
                            operation=PeerCollaborationAssistanceHandleWaitForObjectOperation(
                                assistance_process=self,
                                target_status=AssistanceStateStatus.IN_PROGRESS,
                                parameters=[
                                    AssistanceParameter.create_with_default_parameters(
                                        key=PeerCollaborationAssistance.ASSISTANCE_OPERATION_PARAMETER_KEY_OBJECT_KEY_TO_WAIT_FOR,
                                        value=ASSISTANCE_OBJECT_PARAMETER_KEY_SOLUTION_RESPONSE,
                                    ),
                                    AssistanceParameter.create_with_default_parameters(
                                        key=PeerCollaborationAssistance.ASSISTANCE_OPERATION_PARAMETER_KEY_RECEIVED_OBJECTS_PARAMETER_KEY,
                                        value=PeerCollaborationAssistance.ASSISTANCE_OPERATION_PARAMETER_VALUE_USER_ID_TO_SOLUTION,
                                    ),
                                    AssistanceParameter.create_with_default_parameters(
                                        key=PeerCollaborationAssistanceHandleWaitForObjectOperation.ASSISTANCE_OPERATION_PARAMETER_KEY_RECEIVED_OBJECT_WAITING_FOR_PEER_OBJECTS_TO_SEND,
                                        value=[
                                            AssistanceObject.create_with_parameters_only(
                                                parameters=[
                                                    AssistanceParameter.create_with_default_parameters(
                                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                                                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_NOTES_COMMAND,
                                                    )
                                                ],
                                            ),
                                            AssistanceObject.create_with_parameters_only(
                                                parameters=[
                                                    AssistanceParameter.create_with_default_parameters(
                                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                                                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_NOTES_INPUT,
                                                    )
                                                ],
                                            ),
                                            AssistanceObject.create_with_parameters_only(
                                                parameters=[
                                                    AssistanceParameter.create_with_default_parameters(
                                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE,
                                                        value=t(LOCALE_IDENTIFIER_DE,
                                                                'assistance.peer_collaboration.operation.message_waiting_for_peer_to_provide_solution'),
                                                    )
                                                ],
                                            )
                                        ]
                                    ),
                                    AssistanceParameter.create_with_default_parameters(
                                        key=PeerCollaborationAssistanceHandleWaitForObjectOperation.ASSISTANCE_OPERATION_PARAMETER_KEY_RECEIVED_FINAL_OBJECT_OBJECTS_TO_SEND,
                                        value=[
                                            AssistanceObject.create_with_parameters_only(
                                                parameters=[
                                                    AssistanceParameter.create_with_default_parameters(
                                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                                                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_NOTES_COMMAND,
                                                    )
                                                ],
                                            ),
                                            AssistanceObject.create_with_parameters_only(
                                                parameters=[
                                                    AssistanceParameter.create_with_default_parameters(
                                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                                                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_NOTES_INPUT,
                                                    )
                                                ],
                                            ),
                                        ],
                                    ),
                                ],
                                subsequent_operations=[],
                                delete_scheduled_operations=True
                            ),
                        )
                    ],
                ),
                AssistancePhase(
                    parameters=[
                        AssistanceParameter.create_with_default_parameters(
                            ASSISTANCE_OPERATION_PARAMETER_KEY_TITLE,
                            t(
                                local_identifier,
                                "assistance.peer_collaboration.phase.title_review_solution_peer",
                            ),
                        )
                    ],
                    steps=[
                        AssistancePhaseStep(
                            operation_key="review_solution_peer_step_1",
                            parameters=[],
                            operation=PeerCollaborationAssistanceSendSolutionToPeersOperations(
                                assistance_process=self,
                                target_status=AssistanceStateStatus.IN_PROGRESS,
                                parameters=[],
                                subsequent_operations=[],
                            ),
                            schedule=AssistanceOperationSchedule(
                                time_to_invocation_in_s=1
                            ),
                        ),
                        AssistancePhaseStep(
                            operation_key="review_solution_peer_step_2",
                            parameters=[],
                            operation=PeerCollaborationAssistanceSendObjectsToUsersOperation(
                                assistance_process=self,
                                target_status=AssistanceStateStatus.IN_PROGRESS,
                                parameters=[
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_PEER_SOLUTION_COMMAND,
                                    ),
                                ],
                                subsequent_operations=[SubsequentAssistanceOperation(
                                    type=SubsequentAssistanceOperationType.SCHEDULED_OPERATION,
                                    operation_key="collaboration_step_1",
                                    time_to_invocation_in_s=60 * 3
                                )],
                            ),
                            schedule=AssistanceOperationSchedule(
                                time_to_invocation_in_s=60 * 2
                            ),
                        ),
                        AssistancePhaseStep(
                            operation_key="review_solution_peer_step_3",
                            parameters=[],
                            operation=PeerCollaborationAssistanceHandleWaitForObjectOperation(
                                assistance_process=self,
                                target_status=AssistanceStateStatus.IN_PROGRESS,
                                parameters=[
                                    AssistanceParameter.create_with_default_parameters(
                                        key=PeerCollaborationAssistance.ASSISTANCE_OPERATION_PARAMETER_KEY_OBJECT_KEY_TO_WAIT_FOR,
                                        value=ASSISTANCE_OBJECT_PARAMETER_KEY_STATE_UPDATE_RESPONSE,
                                    ),
                                    AssistanceParameter.create_with_default_parameters(
                                        key=PeerCollaborationAssistance.ASSISTANCE_OPERATION_PARAMETER_KEY_RECEIVED_OBJECTS_PARAMETER_KEY,
                                        value=PeerCollaborationAssistance.ASSISTANCE_OPERATION_PARAMETER_VALUE_USER_ID_TO_READ_SOLUTION_PROGRESS,
                                    ),
                                    AssistanceParameter.create_with_default_parameters(
                                        key=PeerCollaborationAssistance.ASSISTANCE_OPERATION_PARAMETER_KEY_EXPECTED_OBJECT_VALUE,
                                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_STATE_UPDATE_RESPONSE_STANDBY,
                                    ),
                                    AssistanceParameter.create_with_default_parameters(
                                        key=PeerCollaborationAssistanceHandleWaitForObjectOperation.ASSISTANCE_OPERATION_PARAMETER_KEY_RECEIVED_OBJECT_WAITING_FOR_PEER_OBJECTS_TO_SEND,
                                        value=[
                                            AssistanceObject.create_with_parameters_only(
                                                parameters=[
                                                    AssistanceParameter.create_with_default_parameters(
                                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                                                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_PEER_SOLUTION_COMMAND,
                                                    ),
                                                ],
                                            ),
                                            AssistanceObject.create_with_parameters_only(
                                                parameters=[
                                                    AssistanceParameter.create_with_default_parameters(
                                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE,
                                                        value=t(LOCALE_IDENTIFIER_DE,
                                                                'assistance.peer_collaboration.operation.message_waiting_for_peer_to_read_solution'),
                                                    ),
                                                ],
                                            ),
                                        ]
                                    ),
                                ],
                                subsequent_operations=[],
                                delete_scheduled_operations=True
                            ),
                        )
                    ],
                ),
                AssistancePhase(
                    parameters=[
                        AssistanceParameter.create_with_default_parameters(
                            ASSISTANCE_OPERATION_PARAMETER_KEY_TITLE,
                            t(
                                local_identifier,
                                "assistance.peer_collaboration.phase.title_collaboration",
                            ),
                        )
                    ],
                    steps=[
                        AssistancePhaseStep(
                            operation_key="collaboration_step_1",
                            parameters=[],
                            operation=PeerCollaborationAssistanceSendObjectsToUsersOperation(
                                assistance_process=self,
                                target_status=AssistanceStateStatus.IN_PROGRESS,
                                parameters=[
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_PEER_SOLUTION_COMMAND,
                                    ),
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                                        value=t(
                                            LOCALE_IDENTIFIER_DE,
                                            "assistance.peer_collaboration.operation.message_task_description_collaborative_work_part1",
                                        ),
                                    ),
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_CHAT,
                                    )
                                ],
                                subsequent_operations=[SubsequentAssistanceOperation(
                                    type=SubsequentAssistanceOperationType.TRIGGERED_OPERATION,
                                    operation_key=assistance_operation_key_forward_message_to_peer,
                                )],
                            ),
                            schedule=AssistanceOperationSchedule(
                                time_to_invocation_in_s=1
                            ),
                        ),
                        AssistancePhaseStep(
                            operation_key="collaboration_step_2",
                            parameters=[],
                            operation=PeerCollaborationAssistanceSendObjectsToUsersOperation(
                                assistance_process=self,
                                target_status=AssistanceStateStatus.IN_PROGRESS,
                                parameters=[
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE,
                                        value=t(
                                            LOCALE_IDENTIFIER_DE,
                                            "assistance.peer_collaboration.operation.message_hint_collaboration_1",
                                        ),
                                    ),
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE,
                                        value=t(
                                            LOCALE_IDENTIFIER_DE,
                                            "assistance.peer_collaboration.operation.system_message_information_time_for_collaboration_and_exchange",
                                        ),
                                    ),
                                ],
                                subsequent_operations=[SubsequentAssistanceOperation(
                                    type=SubsequentAssistanceOperationType.TRIGGERED_OPERATION,
                                    operation_key=assistance_operation_key_forward_message_to_peer,
                                )],
                            ),
                            schedule=AssistanceOperationSchedule(
                                time_to_invocation_in_s=5
                            ),
                        ),
                        AssistancePhaseStep(
                            operation_key="collaboration_step_3",
                            parameters=[],
                            operation=PeerCollaborationAssistanceSendObjectsToUsersOperation(
                                assistance_process=self,
                                target_status=AssistanceStateStatus.IN_PROGRESS,
                                parameters=[
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE,
                                        value=t(
                                            LOCALE_IDENTIFIER_DE,
                                            "assistance.peer_collaboration.operation.message_hint_collaboration_2",
                                        ),
                                    ),
                                ],
                                subsequent_operations=[SubsequentAssistanceOperation(
                                    type=SubsequentAssistanceOperationType.TRIGGERED_OPERATION,
                                    operation_key=assistance_operation_key_forward_message_to_peer,
                                )],
                            ),
                            schedule=AssistanceOperationSchedule(
                                time_to_invocation_in_s=60 * 5
                            ),
                        ),
                        AssistancePhaseStep(
                            operation_key="collaboration_step_4",
                            parameters=[],
                            operation=PeerCollaborationAssistanceSendObjectsToUsersOperation(
                                assistance_process=self,
                                target_status=AssistanceStateStatus.IN_PROGRESS,
                                parameters=[
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE,
                                        value=t(
                                            LOCALE_IDENTIFIER_DE,
                                            "assistance.peer_collaboration.operation.message_hint_collaboration_3",
                                        ),
                                    ),
                                ],
                                subsequent_operations=[SubsequentAssistanceOperation(
                                    type=SubsequentAssistanceOperationType.TRIGGERED_OPERATION,
                                    operation_key=assistance_operation_key_forward_message_to_peer,
                                )],
                            ),
                            schedule=AssistanceOperationSchedule(
                                time_to_invocation_in_s=60 * 5
                            ),
                        ),
                        AssistancePhaseStep(
                            operation_key="collaboration_step_5",
                            parameters=[],
                            operation=PeerCollaborationAssistanceSendObjectsToUsersOperation(
                                assistance_process=self,
                                target_status=AssistanceStateStatus.IN_PROGRESS,
                                parameters=[
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                                        value=t(
                                            LOCALE_IDENTIFIER_DE,
                                            "assistance.peer_collaboration.operation.system_message_information_time_left_for_collaboration",
                                        ),
                                    ),
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE,
                                        value=t(
                                            LOCALE_IDENTIFIER_DE,
                                            "assistance.peer_collaboration.operation.message_hint_collaboration_4",
                                        ),
                                    ),
                                ],
                                subsequent_operations=[SubsequentAssistanceOperation(
                                    type=SubsequentAssistanceOperationType.TRIGGERED_OPERATION,
                                    operation_key=assistance_operation_key_forward_message_to_peer,
                                )],
                            ),
                            schedule=AssistanceOperationSchedule(
                                time_to_invocation_in_s=60 * 5
                            ),
                        ),
                    ],
                ),
                AssistancePhase(
                    parameters=[
                        AssistanceParameter.create_with_default_parameters(
                            ASSISTANCE_OPERATION_PARAMETER_KEY_TITLE,
                            t(
                                local_identifier,
                                "assistance.peer_collaboration.phase.title_solution_proposal",
                            ),
                        )
                    ],
                    steps=[
                        AssistancePhaseStep(
                            operation_key="solution_proposal_step_1",
                            parameters=[],
                            operation=PeerCollaborationAssistanceSendObjectsToUsersOperation(
                                assistance_process=self,
                                target_status=AssistanceStateStatus.IN_PROGRESS,
                                parameters=[
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_CHAT,
                                    ),
                                    # AssistanceParameter.create_with_default_parameters(
                                    #     key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                                    #     value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_PEER_SOLUTION,
                                    # ),
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                                        value=t(
                                            LOCALE_IDENTIFIER_DE,
                                            "assistance.peer_collaboration.operation.message_task_description_solution_proposal",
                                        ),
                                    ),
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE,
                                        value=t(
                                            LOCALE_IDENTIFIER_DE,
                                            "assistance.peer_collaboration.operation.system_message_information_time_for_individual_solution_proposal_and_exchange_and_solution_provision",
                                        ),
                                    ),
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_NOTES_COMMAND,
                                    ),
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_NOTES_INPUT,
                                    )
                                ],
                                subsequent_operations=[SubsequentAssistanceOperation(
                                    type=SubsequentAssistanceOperationType.TRIGGERED_OPERATION,
                                    operation_key="solution_proposal_step_4",
                                )],
                            ),
                            schedule=AssistanceOperationSchedule(
                                time_to_invocation_in_s=60 * 5
                            ),
                        ),
                        AssistancePhaseStep(
                            operation_key="solution_proposal_step_2",
                            parameters=[],
                            operation=PeerCollaborationAssistanceSendObjectsToUsersOperation(
                                assistance_process=self,
                                target_status=AssistanceStateStatus.IN_PROGRESS,
                                parameters=[
                                    AssistanceParameter.create_with_default_parameters(
                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE,
                                        value=t(
                                            LOCALE_IDENTIFIER_DE,
                                            "assistance.peer_collaboration.operation.system_message_information_time_left_for_solution_proposal",
                                        ),
                                    )
                                ],
                                subsequent_operations=[SubsequentAssistanceOperation(
                                    type=SubsequentAssistanceOperationType.TRIGGERED_OPERATION,
                                    operation_key="solution_proposal_step_4",
                                )],
                            ),
                            schedule=AssistanceOperationSchedule(
                                time_to_invocation_in_s=60 * 8
                            ),
                        ),
                        AssistancePhaseStep(
                            operation_key="solution_proposal_step_3",
                            parameters=[],
                            operation=PeerCollaborationAssistanceRequestSolutionOperation(
                                assistance_process=self,
                                target_status=AssistanceStateStatus.IN_PROGRESS,
                                subsequent_operations=[SubsequentAssistanceOperation(
                                    type=SubsequentAssistanceOperationType.SCHEDULED_OPERATION,
                                    operation_key="solution_proposal_step_3",
                                    time_to_invocation_in_s=2
                                )]
                            ),
                            schedule=AssistanceOperationSchedule(
                                time_to_invocation_in_s=60 * 2
                            ),
                        ),
                        AssistancePhaseStep(
                            operation_key="solution_proposal_step_4",
                            parameters=[],
                            operation=PeerCollaborationAssistanceHandleWaitForObjectOperation(
                                assistance_process=self,
                                target_status=AssistanceStateStatus.COMPLETED,
                                parameters=[
                                    AssistanceParameter.create_with_default_parameters(
                                        key=PeerCollaborationAssistance.ASSISTANCE_OPERATION_PARAMETER_KEY_OBJECT_KEY_TO_WAIT_FOR,
                                        value=ASSISTANCE_OBJECT_PARAMETER_KEY_SOLUTION_RESPONSE,
                                    ),
                                    AssistanceParameter.create_with_default_parameters(
                                        key=PeerCollaborationAssistance.ASSISTANCE_OPERATION_PARAMETER_KEY_RECEIVED_OBJECTS_PARAMETER_KEY,
                                        value=PeerCollaborationAssistance.ASSISTANCE_OPERATION_PARAMETER_VALUE_USER_ID_TO_FINAL_SOLUTION,
                                    ),
                                    AssistanceParameter.create_with_default_parameters(
                                        key=PeerCollaborationAssistanceHandleWaitForObjectOperation.ASSISTANCE_OPERATION_PARAMETER_KEY_RECEIVED_OBJECT_WAITING_FOR_PEER_OBJECTS_TO_SEND,
                                        value=[
                                            AssistanceObject.create_with_parameters_only(
                                                parameters=[
                                                    AssistanceParameter.create_with_default_parameters(
                                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                                                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_NOTES_COMMAND,
                                                    )
                                                ],
                                            ),
                                            AssistanceObject.create_with_parameters_only(
                                                parameters=[
                                                    AssistanceParameter.create_with_default_parameters(
                                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                                                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_NOTES_INPUT,
                                                    )
                                                ],
                                            ),
                                            AssistanceObject.create_with_parameters_only(
                                                parameters=[
                                                    AssistanceParameter.create_with_default_parameters(
                                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                                                        value=t(LOCALE_IDENTIFIER_DE,
                                                                'assistance.peer_collaboration.operation.message_thank_you'),
                                                    )
                                                ],
                                            ),
                                            AssistanceObject.create_with_parameters_only(
                                                parameters=[
                                                    AssistanceParameter.create_with_default_parameters(
                                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                                                        value=t(LOCALE_IDENTIFIER_DE,
                                                                'assistance.peer_collaboration.operation.message_evaluation_link'),
                                                    ),
                                                    AssistanceParameter.create_with_default_parameters(
                                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_URI,
                                                        value=t(LOCALE_IDENTIFIER_DE,
                                                                'assistance.peer_collaboration.operation.evaluation_link'),
                                                    )
                                                ],
                                            )
                                        ],
                                    ),
                                    AssistanceParameter.create_with_default_parameters(
                                        key=PeerCollaborationAssistanceHandleWaitForObjectOperation.ASSISTANCE_OPERATION_PARAMETER_KEY_RECEIVED_FINAL_OBJECT_OBJECTS_TO_SEND,
                                        value=[
                                            AssistanceObject.create_with_parameters_only(
                                                parameters=[
                                                    AssistanceParameter.create_with_default_parameters(
                                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                                                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_NOTES_COMMAND,
                                                    )
                                                ],
                                            ),
                                            AssistanceObject.create_with_parameters_only(
                                                parameters=[
                                                    AssistanceParameter.create_with_default_parameters(
                                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                                                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_NOTES_INPUT,
                                                    )
                                                ],
                                            ),
                                            AssistanceObject.create_with_parameters_only(
                                                parameters=[
                                                    AssistanceParameter.create_with_default_parameters(
                                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                                                        value=t(LOCALE_IDENTIFIER_DE,
                                                                'assistance.peer_collaboration.operation.message_thank_you'),
                                                    )
                                                ],
                                            ),
                                            AssistanceObject.create_with_parameters_only(
                                                parameters=[
                                                    AssistanceParameter.create_with_default_parameters(
                                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                                                        value=t(LOCALE_IDENTIFIER_DE,
                                                                'assistance.peer_collaboration.operation.message_evaluation_link'),
                                                    ),
                                                    AssistanceParameter.create_with_default_parameters(
                                                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_URI,
                                                        value=t(LOCALE_IDENTIFIER_DE,
                                                                'assistance.peer_collaboration.operation.evaluation_link'),
                                                    )
                                                ],
                                            )
                                        ],
                                    ),
                                ],
                                subsequent_operations=[],
                                delete_scheduled_operations=True
                            ),
                        )
                    ],
                ),
            ]
        )


class PeerCollaborationAssistanceForwardMessageToPeerOperation(AssistanceOperation):
    def post_init(self):
        self.assistance_in_progress_required = True

    def is_applicable(self, ctx: AssistanceContext) -> bool:
        if not super().is_applicable(ctx):
            return False
        try:
            # TODO: May there be any parallel operation?
            ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_ASSISTANCE_OBJECTS)
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


class PeerCollaborationAssistanceHandleWaitForObjectOperation(AssistanceOperation):
    ASSISTANCE_OPERATION_PARAMETER_KEY_RECEIVED_FINAL_OBJECT_OBJECTS_TO_SEND = "reveived_final_object_objects_to_send"
    ASSISTANCE_OPERATION_PARAMETER_KEY_RECEIVED_OBJECT_WAITING_FOR_PEER_OBJECTS_TO_SEND = "reveived_object_waiting_for_peer_objects_to_send"

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
            object_parameter_key = get_first_assistance_parameter_by_key(
                self.parameters,
                PeerCollaborationAssistance.ASSISTANCE_OPERATION_PARAMETER_KEY_OBJECT_KEY_TO_WAIT_FOR,
            ).value
            expected_parameter_key_contained = False
            for received_assistance_object in received_assistance_objects:
                try:
                    get_first_assistance_parameter_by_key(received_assistance_object.parameters, object_parameter_key)
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
        received_assistance_objects = ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_ASSISTANCE_OBJECTS)

        object_parameter_key = get_first_assistance_parameter_by_key(
            self.parameters,
            PeerCollaborationAssistance.ASSISTANCE_OPERATION_PARAMETER_KEY_OBJECT_KEY_TO_WAIT_FOR,
        ).value

        provided_object_value = None
        user_id = None
        for received_assistance_object in received_assistance_objects:
            try:
                provided_object_value = get_first_assistance_parameter_by_key(
                    received_assistance_object.parameters, object_parameter_key).value
                user_id = received_assistance_object.user_id
                break
            except AssistanceParameterException:
                pass
        if provided_object_value is None or user_id is None:
            return None

        try:
            expected_object_value = get_first_assistance_parameter_by_key(
                self.parameters,
                PeerCollaborationAssistance.ASSISTANCE_OPERATION_PARAMETER_KEY_EXPECTED_OBJECT_VALUE).value
            if provided_object_value != expected_object_value:
                return None
        except AssistanceParameterException:
            pass

        self.related_user_ids = [user_id]

        received_objects_parameter_key = get_first_assistance_parameter_by_key(
            self.parameters,
            PeerCollaborationAssistance.ASSISTANCE_OPERATION_PARAMETER_KEY_RECEIVED_OBJECTS_PARAMETER_KEY,
        ).value

        try:
            already_received_objects = get_first_assistance_parameter_by_key(
                assistance.parameters,
                received_objects_parameter_key).value
        except AssistanceParameterException:
            already_received_objects = {}

        repeated_object_provision = user_id in already_received_objects

        if not repeated_object_provision:
            already_received_objects[user_id] = provided_object_value
            assistance.parameters = replace_or_add_assistance_parameters_by_key(
                AssistanceParameter.create_with_default_parameters(
                    received_objects_parameter_key,
                    already_received_objects,
                ), assistance.parameters
            )

        received_object_waiting_for_peer_objects_to_send = get_first_assistance_parameter_by_key(
            self.parameters,
            self.ASSISTANCE_OPERATION_PARAMETER_KEY_RECEIVED_OBJECT_WAITING_FOR_PEER_OBJECTS_TO_SEND
        ).value
        try:
            received_final_object_objects_to_send = get_first_assistance_parameter_by_key(
                self.parameters,
                self.ASSISTANCE_OPERATION_PARAMETER_KEY_RECEIVED_FINAL_OBJECT_OBJECTS_TO_SEND,
            ).value
        except AssistanceParameterException:
            received_final_object_objects_to_send = []

        all_solutions_provided = len(already_received_objects) == len(related_user_ids)
        logger.debug(
            f"Received {len(already_received_objects)} of {len(related_user_ids)} objects while waiting for {object_parameter_key}")
        if all_solutions_provided:
            self.prevent_progress = False
            for received_final_object_object_to_send in received_final_object_objects_to_send:
                received_final_object_object_to_send.user_id = user_id
            assistance.parameters = list(
                filter(lambda
                           parameter: parameter.key != PeerCollaborationAssistanceRequestSolutionOperation.ASSISTANCE_PARAMETER_KEY_SOLUTION_REQUEST_NUMBER,
                       assistance.parameters))
            assistance.assistance_objects = received_final_object_objects_to_send
        else:
            self.prevent_progress = True
            if repeated_object_provision:
                return None
            for received_object_waiting_for_peer_object_to_send in received_object_waiting_for_peer_objects_to_send:
                received_object_waiting_for_peer_object_to_send.user_id = user_id
            assistance.assistance_objects = received_object_waiting_for_peer_objects_to_send

        return AssistanceResult(assistance=[assistance])


class PeerCollaborationAssistanceInitiationOperation(AssistanceOperation):
    def is_applicable(self, ctx: AssistanceContext) -> bool:
        try:
            ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_STATEMENT_ID)
            return False
        except AssistanceParameterException:
            # This is expected
            pass
        try:
            ctx.get_parameter(
                PeerCollaborationAssistance.ASSISTANCE_TYPE_PARAMETER_KEY_USER_ID_INITIATOR
            )
            ctx.get_parameter(
                PeerCollaborationAssistance.ASSISTANCE_TYPE_PARAMETER_KEY_USER_IDS_COLLABORATORS
            )
        except AssistanceParameterException:
            return False
        return True

    def _execute(self, ctx: AssistanceContext) -> AssistanceResult | None:
        user_id = ctx.get_parameter(
            PeerCollaborationAssistance.ASSISTANCE_TYPE_PARAMETER_KEY_USER_ID_INITIATOR
        )
        related_user_ids = ctx.get_parameter(
            PeerCollaborationAssistance.ASSISTANCE_TYPE_PARAMETER_KEY_USER_IDS_COLLABORATORS
        )

        assistance_to_initiate = []
        for i in range(0, len(related_user_ids) if len(related_user_ids) % 2 == 0 else len(related_user_ids) - 1, 2):
            user_ids_collaborators = related_user_ids[i:i + 2]
            assistance_objects_to_send = []
            for j, collaborator_id in enumerate(user_ids_collaborators):
                parameters_to_send = [
                    AssistanceParameter.create_with_default_parameters(
                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_CHAT,
                    ),
                    AssistanceParameter.create_with_default_parameters(
                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_RESET_NOTES,
                    ),
                    AssistanceParameter.create_with_default_parameters(
                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_NOTES,
                    ),
                    AssistanceParameter.create_with_default_parameters(
                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_NOTES_COMMAND,
                    ),
                    AssistanceParameter.create_with_default_parameters(
                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_NOTES_INPUT,
                    ),
                    AssistanceParameter.create_with_default_parameters(
                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_PEER_SOLUTION,
                    ),
                    AssistanceParameter.create_with_default_parameters(
                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_DISABLE_PEER_SOLUTION_COMMAND,
                    ),
                    AssistanceParameter.create_with_default_parameters(
                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                        value=t(LOCALE_IDENTIFIER_DE,
                                'assistance.peer_collaboration.operation.message_task_description_part1'),
                    ),
                    AssistanceParameter.create_with_default_parameters(
                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                        value=t(LOCALE_IDENTIFIER_DE,
                                'assistance.peer_collaboration.operation.message_task_description_part2'),
                    )
                ]

                for parameter_to_send in parameters_to_send:
                    assistance_objects_to_send.append(AssistanceObject.create_with_default_parameters(
                        user_id=collaborator_id,
                        parameters=[parameter_to_send]))

            assistance = Assistance.create_with_default_parameters(
                user_id=user_id,
                assistance_objects=assistance_objects_to_send,
            )
            assistance.parameters = [
                AssistanceParameter.create_with_default_parameters(
                    ASSISTANCE_PARAMETER_KEY_RELATED_USER_IDS,
                    user_ids_collaborators,
                )
            ]
            assistance_to_initiate.append(assistance)

        return AssistanceResult(assistance=assistance_to_initiate)


class PeerCollaborationAssistanceRequestSolutionOperation(AssistanceOperation):
    MAX_NUMBER_OF_RETRIES = 17
    ASSISTANCE_PARAMETER_KEY_SOLUTION_REQUEST_NUMBER = 'solution_request_number_of_retries'

    def post_init(self):
        self.assistance_in_progress_required = True

    def _execute(self, ctx: AssistanceContext) -> AssistanceResult | None:
        assistance = read_assistance_by_a_id(
            ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_A_ID)
        )
        related_user_ids = get_first_assistance_parameter_by_key(
            assistance.parameters,
            ASSISTANCE_PARAMETER_KEY_RELATED_USER_IDS,
        ).value

        try:
            solution_request_number = get_first_assistance_parameter_by_key(
                assistance.parameters,
                self.ASSISTANCE_PARAMETER_KEY_SOLUTION_REQUEST_NUMBER,
            ).value + 1
        except AssistanceParameterException:
            solution_request_number = 1

        if solution_request_number + 1 > self.MAX_NUMBER_OF_RETRIES:
            self.delete_scheduled_operations = True
            self.reset_next_operation_keys = True
            self.subsequent_operations = []
            self.target_status = AssistanceStateStatus.ABORTED
            assistance.assistance_objects = list(map(
                lambda user_id:
                AssistanceObject.create_with_default_parameters(
                    user_id=user_id,
                    parameters=[
                        AssistanceParameter.create_with_default_parameters(
                            key=ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE,
                            value=t(LOCALE_IDENTIFIER_DE,
                                    'assistance.peer_collaboration.operation.system_message_scenario_aborted'),
                        )
                    ]
                ), related_user_ids
            ))
            return AssistanceResult(assistance=[assistance])

        if self.step is None or self.step not in self.assistance_process.registered_operation_keys_to_step_number:
            return None
        operation_key = self.step

        assistance_objects_to_send = []
        step_number = self.assistance_process.registered_operation_keys_to_step_number[self.step]
        try:
            user_states = get_first_assistance_parameter_by_key(
                assistance.parameters,
                ASSISTANCE_PARAMETER_KEY_USER_ID_TO_STATE).value
        except AssistanceParameterException:
            user_states = {}
        for related_user_id in related_user_ids:
            if related_user_id in user_states and user_states[related_user_id].step is not None and \
                    self.assistance_process.registered_operation_keys_to_step_number[
                        user_states[related_user_id].step] < step_number:
                continue
            assistance_objects_to_send.append(AssistanceObject.create_with_default_parameters(
                user_id=related_user_id,
                parameters=[
                    AssistanceParameter.create_with_default_parameters(
                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                        value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_SEND_SOLUTION,
                    )
                ]
            ))

        assistance.assistance_objects = assistance_objects_to_send

        # Adjust time for next solution request
        for i, subsequent_operation in enumerate(self.subsequent_operations):
            if subsequent_operation.type != SubsequentAssistanceOperationType.SCHEDULED_OPERATION or subsequent_operation.operation_key != operation_key:
                continue
            self.subsequent_operations[i] = SubsequentAssistanceOperation(
                type=SubsequentAssistanceOperationType.SCHEDULED_OPERATION,
                operation_key=operation_key,
                time_to_invocation_in_s=fibonacci(start=2, length=solution_request_number)[-1:][0]
            )

        # Replace retry parameter
        assistance.parameters = replace_or_add_assistance_parameters_by_key(
            AssistanceParameter.create_with_default_parameters(
                self.ASSISTANCE_PARAMETER_KEY_SOLUTION_REQUEST_NUMBER,
                solution_request_number,
            ), assistance.parameters
        )

        return AssistanceResult(assistance=[assistance])


class PeerCollaborationAssistanceSendGroupFormationResultToPeersOperation(AssistanceOperation):
    def post_init(self):
        self.assistance_in_progress_required = True

    def _execute(self, ctx: AssistanceContext) -> AssistanceResult | None:
        assistance = read_assistance_by_a_id(
            ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_A_ID)
        )
        related_user_ids = get_first_assistance_parameter_by_key(
            assistance.parameters,
            ASSISTANCE_PARAMETER_KEY_RELATED_USER_IDS,
        ).value

        user_parameters = list(map(lambda related_user_id: AssistanceParameter.create_with_default_parameters(
            key=ASSISTANCE_OBJECT_PARAMETER_KEY_USER_ID,
            value=related_user_id,
        ), related_user_ids))

        assistance_objects_to_send = []
        for user_id in related_user_ids:
            assistance_objects_to_send.append(AssistanceObject.create_with_default_parameters(
                user_id=user_id,
                parameters=[
                    AssistanceParameter.create_with_default_parameters(
                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                        value=t(LOCALE_IDENTIFIER_DE,
                                'assistance.peer_collaboration.operation.message_peer_found'),
                    ),
                    AssistanceParameter.create_with_default_parameters(
                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_RELATED_USERS,
                        value=user_parameters,
                    )
                ],
            ))

        assistance.assistance_objects = assistance_objects_to_send
        return AssistanceResult(assistance=[assistance])


class PeerCollaborationAssistanceSendGroupInformationOperation(AssistanceOperation):
    def post_init(self):
        self.assistance_in_progress_required = True

    def _execute(self, ctx: AssistanceContext) -> AssistanceResult | None:
        assistance = read_assistance_by_a_id(
            ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_A_ID)
        )
        related_user_ids = get_first_assistance_parameter_by_key(
            assistance.parameters,
            ASSISTANCE_PARAMETER_KEY_RELATED_USER_IDS,
        ).value

        assistance_objects_to_send = []
        for i, user_id in enumerate(related_user_ids):
            assistance_objects_to_send.append(AssistanceObject.create_with_default_parameters(
                user_id=user_id,
                parameters=[
                    AssistanceParameter.create_with_default_parameters(
                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE,
                        value=t(LOCALE_IDENTIFIER_DE,
                                'assistance.peer_collaboration.operation.system_message_information_about_group_assignment',
                                group=chr(ord("@") + (i + 1))),
                    )
                ],
            ))

        assistance.assistance_objects = assistance_objects_to_send
        return AssistanceResult(assistance=[assistance])


class PeerCollaborationAssistanceSendObjectsToUsersOperation(AssistanceOperation):
    ASSISTANCE_OPERATION_PARAMETER_KEYS = [
        ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
        ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
        ASSISTANCE_OBJECT_PARAMETER_KEY_SOLUTION_TEMPLATE,
        ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE
    ]

    def post_init(self):
        self.assistance_in_progress_required = True

    def _execute(self, ctx: AssistanceContext) -> AssistanceResult | None:
        assistance = read_assistance_by_a_id(
            ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_A_ID)
        )
        related_user_ids = get_first_assistance_parameter_by_key(
            assistance.parameters,
            ASSISTANCE_PARAMETER_KEY_RELATED_USER_IDS,
        ).value
        parameters_to_send = get_assistance_parameters_by_keys(
            self.parameters,
            PeerCollaborationAssistanceSendObjectsToUsersOperation.ASSISTANCE_OPERATION_PARAMETER_KEYS)

        # Filter user ids for users that already went on
        user_ids_to_send_objects_to = []
        if self.step is not None and self.step in self.assistance_process.registered_operation_keys_to_step_number:
            step_number = self.assistance_process.registered_operation_keys_to_step_number[self.step]
            try:
                user_states = get_first_assistance_parameter_by_key(
                    assistance.parameters,
                    ASSISTANCE_PARAMETER_KEY_USER_ID_TO_STATE).value
            except AssistanceParameterException:
                user_states = {}
            for related_user_id in related_user_ids:
                if related_user_id not in user_states:
                    user_ids_to_send_objects_to.append(related_user_id)
                    continue
                user_state = user_states[related_user_id]
                if user_state.step is None:
                    user_ids_to_send_objects_to.append(related_user_id)
                    continue
                if self.assistance_process.registered_operation_keys_to_step_number[user_state.step] <= step_number:
                    user_ids_to_send_objects_to.append(related_user_id)
        else:
            user_ids_to_send_objects_to = related_user_ids
        self.related_user_ids = user_ids_to_send_objects_to

        assistance_objects = []
        for parameter_to_send in parameters_to_send:
            assistance_objects += list(
                map(
                    lambda collaborator_id: AssistanceObject.create_with_default_parameters(
                        user_id=collaborator_id,
                        parameters=[parameter_to_send],
                    ),
                    user_ids_to_send_objects_to,
                )
            )

        assistance.assistance_objects = assistance_objects
        return AssistanceResult(assistance=[assistance])


class PeerCollaborationAssistanceSendSolutionToPeersOperations(AssistanceOperation):
    def post_init(self):
        self.assistance_in_progress_required = True

    def _execute(self, ctx: AssistanceContext) -> AssistanceResult | None:
        assistance = read_assistance_by_a_id(
            ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_A_ID)
        )
        related_user_ids = get_first_assistance_parameter_by_key(
            assistance.parameters,
            ASSISTANCE_PARAMETER_KEY_RELATED_USER_IDS,
        ).value
        # FIXME: Abort if no solution
        solutions = get_first_assistance_parameter_by_key(
            assistance.parameters,
            PeerCollaborationAssistance.ASSISTANCE_OPERATION_PARAMETER_VALUE_USER_ID_TO_SOLUTION).value

        assistance_objects_to_send = []
        for user_id, solution in solutions.items():
            assistance_objects_to_send += list(
                map(lambda peer_to_send_solution_to: AssistanceObject.create_with_default_parameters(
                    user_id=peer_to_send_solution_to,
                    parameters=[
                        AssistanceParameter.create_with_default_parameters(
                            key=ASSISTANCE_OBJECT_PARAMETER_KEY_PEER_SOLUTION,
                            value=solution,
                        )
                    ],
                ), list(filter(lambda related_user_id: related_user_id != user_id, related_user_ids))))
            assistance_objects_to_send += [
                AssistanceObject.create_with_default_parameters(
                    user_id=user_id,
                    parameters=[
                        AssistanceParameter.create_with_default_parameters(
                            key=ASSISTANCE_OBJECT_PARAMETER_KEY_OPERATION,
                            value=ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ENABLE_PEER_SOLUTION,
                        ),
                    ],
                ),
                AssistanceObject.create_with_default_parameters(
                    user_id=user_id,
                    parameters=[
                        AssistanceParameter.create_with_default_parameters(
                            key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                            value=t(
                                LOCALE_IDENTIFIER_DE,
                                "assistance.peer_collaboration.operation.message_task_description_read_peer_solution",
                            ),
                        ),
                    ],
                ),
                AssistanceObject.create_with_default_parameters(
                    user_id=user_id,
                    parameters=[
                        AssistanceParameter.create_with_default_parameters(
                            key=ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE,
                            value=t(
                                LOCALE_IDENTIFIER_DE,
                                "assistance.peer_collaboration.operation.system_message_information_time_for_read_peer_solution",
                            ),
                        ),
                    ],
                ),
            ]

        assistance.assistance_objects = assistance_objects_to_send
        return AssistanceResult(assistance=[assistance])
