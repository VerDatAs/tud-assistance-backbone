"""
    Assistance Backbone for the assistance system developed as part of the VerDatAs project
    Copyright (C) 2022-2024 TU Dresden (Robert Schmidt, Sebastian Kucharski)

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

from assistance import get_first_assistance_parameter_by_key
from assistance.reactive_assistance import ReactiveAssistanceProcess
from error.tutorial_module import AssistanceParameterException
from model.core.tutorial_module import (
    AssistanceObject,
    AssistanceParameter,
    AssistanceStateStatus, AssistanceParameterType, AssistanceParameterSearchCriteria, Assistance,
)
from model.service.assistance import (
    AssistanceContext,
    AssistanceResult,
    AssistanceOperation,
    ASSISTANCE_TYPE_PARAMETER_KEY_USER_ID,
    ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ASK_AI, ASSISTANCE_OPERATION_KEY_INITIATION,
    ASSISTANCE_OBJECT_PARAMETER_KEY_QUESTION_FOR_AI_RESPONSE, ASSISTANCE_TYPE_PARAMETER_KEY_USER_ID_INITIATOR,
    ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
)
from service.db.assistance import read_assistance_by_search_criteria
from service.ollama import OllamaApi


class AskAiForHelpAssistance(ReactiveAssistanceProcess):
    @staticmethod
    def get_key() -> str:
        return ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ASK_AI

    @staticmethod
    def get_parameters() -> List[AssistanceParameter] | None:
        return [
            AssistanceParameter.create_with_default_definition_parameters(
                key=ASSISTANCE_TYPE_PARAMETER_KEY_USER_ID,
                type=AssistanceParameterType.STRING,
                required=True,
            ),
            AssistanceParameter.create_with_default_definition_parameters(
                key=ASSISTANCE_OBJECT_PARAMETER_KEY_QUESTION_FOR_AI_RESPONSE,
                type=AssistanceParameterType.STRING,
                required=True,
            ),
        ]

    def __init__(self) -> None:
        super().__init__()

        self._register_operation(
            ASSISTANCE_OPERATION_KEY_INITIATION,
            AskAiForHelpAssistanceInitiationOperation(
                assistance_process=self,
                target_status=AssistanceStateStatus.COMPLETED
            ),
        )


class AskAiForHelpAssistanceInitiationOperation(AssistanceOperation):
    def is_applicable(self, ctx: AssistanceContext) -> bool:
        try:
            ctx.get_parameter(
                ASSISTANCE_TYPE_PARAMETER_KEY_USER_ID
            )
            ctx.get_parameter(
                ASSISTANCE_OBJECT_PARAMETER_KEY_QUESTION_FOR_AI_RESPONSE
            )
            return True
        except AssistanceParameterException:
            return False

    def _execute(self, ctx: AssistanceContext) -> AssistanceResult | None:
        user_id = ctx.get_parameter(ASSISTANCE_TYPE_PARAMETER_KEY_USER_ID_INITIATOR)
        question = ctx.get_parameter(ASSISTANCE_OBJECT_PARAMETER_KEY_QUESTION_FOR_AI_RESPONSE)

        assistance_search_criteria = AssistanceParameterSearchCriteria({
            "key": "typeKey",
            "value": ASSISTANCE_OBJECT_PARAMETER_VALUE_OPERATION_ASK_AI
        })
        assistance_list = read_assistance_by_search_criteria([assistance_search_criteria])

        questions_by_assistance_id = {}
        answers_by_assistance_id = {}
        for assistance in assistance_list.assistanceRecords:
            for assistance_object in assistance.assistance_objects:
                questions_by_assistance_id[assistance.a_id] = get_first_assistance_parameter_by_key(
                    assistance_object.parameters, ASSISTANCE_OBJECT_PARAMETER_KEY_QUESTION_FOR_AI_RESPONSE)
                answers_by_assistance_id[assistance.a_id] = get_first_assistance_parameter_by_key(
                    assistance_object.parameters, ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE)

        # FIXME: add information to prompt how to proceed with prior questions
        answer = OllamaApi.chat(question)

        return AssistanceResult(assistance=[Assistance.create_with_default_parameters(
            user_id=user_id,
            assistance_objects=[
                AssistanceObject.create_with_default_parameters(
                    user_id=user_id,
                    parameters=[
                        AssistanceParameter.create_with_default_parameters(
                            key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                            value=answer,
                        )
                    ]
                )
            ],
        )])
