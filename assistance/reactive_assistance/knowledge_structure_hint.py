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

from assistance import get_first_assistance_parameter_by_key
from assistance.reactive_assistance import ReactiveAssistanceProcess
from error.student_module import StudentModelNotExistsError
from error.tutorial_module import AssistanceParameterException
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
    ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE, ASSISTANCE_OBJECT_PARAMETER_KEY_URI,
)
from service.db.assistance_object import read_assistance_objects_by_user_id_and_parameter
from service.db.experience import read_experiences_by_user_id_and_object_id_and_verb_id, \
    read_experiences_by_user_id_and_object_ids
from service.db.learning_content_object import read_learning_content_object_by_object_id
from service.db.statement import read_statement_by_id
from service.db.student_model import read_student_model_by_user_id
from service.i18n import t, LOCALE_IDENTIFIER_DE
from service.learning_content_object import get_sub_learning_content_object_object_ids
from service.statement import get_user_id, ilias_statement_references_course


class KnowledgeStructureHintAssistance(ReactiveAssistanceProcess):
    @staticmethod
    def get_key() -> str:
        return "knowledge_structure_hint"

    def __init__(self) -> None:
        super().__init__()
        self._register_operation(
            ASSISTANCE_OPERATION_KEY_INITIATION,
            KnowledgeStructureHintInitiationOperation(
                assistance_process=self,
                target_status=AssistanceStateStatus.COMPLETED,
            ),
        )


class KnowledgeStructureHintInitiationOperation(AssistanceOperation):
    def is_applicable(self, ctx: AssistanceContext) -> bool:
        try:
            statement = read_statement_by_id(
                ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_STATEMENT_ID)
            )
            if statement is None or statement.verb.id != StatementVerbId.EXPERIENCED.value:
                return False
            return ilias_statement_references_course(statement.object.id)
        except (AssistanceParameterException | AttributeError):
            return False

    def _execute(self, ctx: AssistanceContext) -> AssistanceResult | None:
        statement = read_statement_by_id(ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_STATEMENT_ID))
        user_id = get_user_id(
            statement
        )
        student_model = read_student_model_by_user_id(user_id=user_id)
        if student_model is None:
            raise StudentModelNotExistsError()

        object_id = statement.object.id
        object_experienced_experiences = read_experiences_by_user_id_and_object_id_and_verb_id(
            user_id=user_id, object_id=object_id, verb_id=StatementVerbId.EXPERIENCED.value)

        assistance_objects = []
        if len(object_experienced_experiences) <= 1:
            assistance_objects.append(
                AssistanceObject.create_with_default_parameters(
                    user_id=user_id,
                    parameters=[
                        AssistanceParameter.create_with_default_parameters(
                            key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                            value=t(LOCALE_IDENTIFIER_DE,
                                    "assistance.knowledge_structure_hint.operation.message_introduction_knowledge_graph"),
                        )
                    ],
                ),
            )
        elif 1 < len(object_experienced_experiences) <= 2:
            assistance_objects.append(
                AssistanceObject.create_with_default_parameters(
                    user_id=user_id,
                    parameters=[
                        AssistanceParameter.create_with_default_parameters(
                            key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                            value=t(LOCALE_IDENTIFIER_DE,
                                    "assistance.knowledge_structure_hint.operation.message_introduction_progress_indication"),
                        )
                    ],
                )
            )
        else:
            lco = read_learning_content_object_by_object_id(object_id)
            if lco is None:
                return None
            message_parameter = AssistanceParameter.create_with_default_parameters(
                key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                value=t(LOCALE_IDENTIFIER_DE,
                        "assistance.knowledge_structure_hint.operation.message_ask_for_jumping_to_last_state"),
            )
            previous_assistance_objects = sorted(read_assistance_objects_by_user_id_and_parameter(
                user_id=user_id, parameter=message_parameter), key=lambda ao: ao.timestamp, reverse=True)
            sub_lco_experiences = sorted(read_experiences_by_user_id_and_object_ids(
                user_id=user_id, object_ids=get_sub_learning_content_object_object_ids(lco)),
                key=lambda sub_lco_experience: sub_lco_experience.timestamp, reverse=True)
            if len(sub_lco_experiences) == 0:
                return None
            last_experienced_object_id = sub_lco_experiences[0].object_id
            if len(previous_assistance_objects) != 0:
                try:
                    last_object_id_provided_to_user = get_first_assistance_parameter_by_key(
                        previous_assistance_objects[0].parameters,
                        ASSISTANCE_OBJECT_PARAMETER_KEY_URI).value
                    if last_object_id_provided_to_user == last_experienced_object_id:
                        return None
                except AttributeError:
                    pass

            assistance_objects.append(
                AssistanceObject.create_with_default_parameters(
                    user_id=user_id,
                    parameters=[
                        message_parameter,
                        AssistanceParameter.create_with_default_parameters(
                            key=ASSISTANCE_OBJECT_PARAMETER_KEY_URI,
                            value=last_experienced_object_id,
                        )
                    ],
                )
            )

        return AssistanceResult(
            assistance=[
                Assistance.create_with_default_parameters(
                    user_id=user_id,
                    assistance_objects=assistance_objects,
                )
            ]
        )
