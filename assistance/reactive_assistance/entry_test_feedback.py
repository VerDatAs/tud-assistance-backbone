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

from assistance.reactive_assistance import ReactiveAssistanceProcess
from error.student_module import StudentModelNotExistsError
from error.tutorial_module import AssistanceParameterException
from model.core.expert_module import LCO_ATTRIBUTE_KEY_ENTRY_TEST_INDICATOR
from model.core.student_module import StatementVerbId, Experience, ExperienceVerbId, TestEvaluationResult
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
    ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
)
from service.datetime import current_datetime
from service.db.experience import create_experience
from service.db.learning_content_object import read_learning_content_object_by_object_id
from service.db.statement import read_statement_by_id
from service.db.student_model import read_student_model_by_user_id
from service.i18n import t, LOCALE_IDENTIFIER_DE
from service.learning_content_object import get_learning_content_object_attribute_value, get_root_lco
from service.statement import get_user_id


class EntryTestFeedbackAssistance(ReactiveAssistanceProcess):
    @staticmethod
    def get_key() -> str:
        return "entry_test_feedback"

    def __init__(self) -> None:
        super().__init__()
        self._register_operation(
            ASSISTANCE_OPERATION_KEY_INITIATION,
            EntryTestFeedbackAssistanceInitiationOperation(
                assistance_process=self,
                target_status=AssistanceStateStatus.COMPLETED,
            ),
        )


class EntryTestFeedbackAssistanceInitiationOperation(AssistanceOperation):
    def is_applicable(self, ctx: AssistanceContext) -> bool:
        try:
            statement = read_statement_by_id(
                ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_STATEMENT_ID)
            )
            if statement is None or statement.verb.id != StatementVerbId.COMPLETED.value or statement.result is None:
                return False
            lco = read_learning_content_object_by_object_id(statement.object.id)
            if lco is None:
                return False
            entry_test_indicator_attribute_value = get_learning_content_object_attribute_value(
                lco=lco, lco_attribute_key=LCO_ATTRIBUTE_KEY_ENTRY_TEST_INDICATOR)
            return entry_test_indicator_attribute_value is not None and entry_test_indicator_attribute_value is True

        except (AssistanceParameterException | AttributeError):
            return False

    def _execute(self, ctx: AssistanceContext) -> AssistanceResult | None:
        statement = read_statement_by_id(ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_STATEMENT_ID))
        user_id = get_user_id(
            statement
        )

        try:
            user_is_expert = statement.result.score.scaled > 0.9
        except Exception:
            return None
        message = t(LOCALE_IDENTIFIER_DE,
                    "assistance.entry_test_feedback.operation.message_user_is_expert" if user_is_expert
                    else "assistance.entry_test_feedback.operation.message_user_is_no_expert")

        student_model = read_student_model_by_user_id(user_id=user_id)
        if student_model is None:
            raise StudentModelNotExistsError()

        object_id = statement.object.id
        lco = read_learning_content_object_by_object_id(object_id)
        root_lco = get_root_lco(lco)

        create_experience(Experience.create_with_default_parameters_and_lco_id(
            timestamp=current_datetime(),
            statement_id=statement.id,
            object_id=root_lco.object_id,
            verb_id=ExperienceVerbId.ENTRY_TEST_EVALUATED.value,
            lco_id=root_lco.lco_id,
            result=TestEvaluationResult.EXPERT.value if user_is_expert else TestEvaluationResult.NO_EXPERT.value),
            user_id)

        return AssistanceResult(
            assistance=[
                Assistance.create_with_default_parameters(
                    user_id=user_id,
                    assistance_objects=[
                        AssistanceObject.create_with_default_parameters(
                            user_id=user_id,
                            parameters=[
                                AssistanceParameter.create_with_default_parameters(
                                    key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                                    value=message,
                                )
                            ],
                        )
                    ],
                )
            ]
        )
