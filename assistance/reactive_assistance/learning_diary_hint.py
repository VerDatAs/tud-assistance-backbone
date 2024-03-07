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

from assistance.reactive_assistance import ReactiveAssistanceProcess
from error.student_module import StudentModelNotExistsError
from error.tutorial_module import AssistanceParameterException
from model.core.expert_module import LearningContentObject
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
    ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE, )
from service.db.experience import read_experiences_by_user_id_and_object_ids
from service.db.learning_content_object import read_learning_content_object_by_object_id
from service.db.statement import read_statement_by_id
from service.db.student_model import read_student_model_by_user_id
from service.i18n import t, LOCALE_IDENTIFIER_DE
from service.learning_content_object import get_root_lco, \
    get_sub_learning_content_objects
from service.statement import get_user_id


class LearningDiaryHintAssistance(ReactiveAssistanceProcess):
    @staticmethod
    def get_key() -> str:
        return "learning_diary_hint"

    def __init__(self) -> None:
        super().__init__()
        self._register_operation(
            ASSISTANCE_OPERATION_KEY_INITIATION,
            LearningDiaryHintInitiationOperation(
                assistance_process=self,
                target_status=AssistanceStateStatus.COMPLETED,
            ),
        )


class LearningDiaryHintInitiationOperation(AssistanceOperation):
    CONTENT_PAGE_TYPE = "ILIAS_CONTENT_PAGE"
    LEARNING_DIARY_TYPE = "ILIAS_DOCUMENTATION_TOOL"

    def is_applicable(self, ctx: AssistanceContext) -> bool:
        try:
            statement = read_statement_by_id(
                ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_STATEMENT_ID)
            )
            if statement is None or statement.verb.id != StatementVerbId.EXPERIENCED.value:
                return False
            lco = read_learning_content_object_by_object_id(statement.object.id)
            if lco is None or lco.lco_type != self.CONTENT_PAGE_TYPE or lco.attributes is None or (not lco.attributes):
                return False
            learning_diary_contained_on_page = False
            for attribute in lco.attributes:
                if type(attribute.value) is LearningContentObject:
                    learning_diary_contained_on_page = attribute.value.lco_type == self.LEARNING_DIARY_TYPE
                elif type(attribute.value) is list:
                    for value_element in attribute.value:
                        if type(value_element) is LearningContentObject:
                            learning_diary_contained_on_page = value_element.lco_type == self.LEARNING_DIARY_TYPE
                        if learning_diary_contained_on_page:
                            break
                if learning_diary_contained_on_page:
                    break
            return learning_diary_contained_on_page
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
        lco = read_learning_content_object_by_object_id(object_id)
        if lco is None:
            return None

        root_lco = get_root_lco(lco)
        sub_lcos = [sub_lco for sub_lco in get_sub_learning_content_objects(root_lco) if
                    sub_lco.lco_type == self.LEARNING_DIARY_TYPE]

        referenced_learning_diaries = []
        lco = read_learning_content_object_by_object_id(statement.object.id)
        for attribute in lco.attributes:
            if type(attribute.value) is LearningContentObject and attribute.value.lco_type == self.LEARNING_DIARY_TYPE:
                referenced_learning_diaries.append(attribute.value)
            elif type(attribute.value) is list:
                for value_element in attribute.value:
                    if type(value_element) is LearningContentObject and value_element.lco_type == self.LEARNING_DIARY_TYPE:
                        referenced_learning_diaries.append(value_element)
        referenced_documentation_tool_object_ids = [learning_diary_lco.object_id for learning_diary_lco in
                                                    referenced_learning_diaries]

        if len(sub_lcos) == 0:
            logger.warning(f"Analyzed root LCO that should but does not contain a learning diary element!")
            return None
        if len(sub_lcos) == 1:
            is_first_documentation_tool = True
            is_last_documentation_tool = False
        else:
            is_first_documentation_tool = sub_lcos[0].object_id == referenced_documentation_tool_object_ids[0]
            is_last_documentation_tool = sub_lcos[-1].object_id == referenced_documentation_tool_object_ids[-1]

        learning_diary_page_experiences = read_experiences_by_user_id_and_object_ids(user_id=user_id,
                                                                                     object_ids=[object_id])

        if is_first_documentation_tool:
            message = t(LOCALE_IDENTIFIER_DE,
                        "assistance.learning_diary_hint.operation.message_usage_hint_first_learning_diary" if len(
                            learning_diary_page_experiences) <= 1 else "assistance.learning_diary_hint.operation.message_usage_second_hint_first_learning_diary")
        elif is_last_documentation_tool:
            message = t(LOCALE_IDENTIFIER_DE,
                        "assistance.learning_diary_hint.operation.message_usage_hint_last_learning_diary" if len(
                            learning_diary_page_experiences) <= 1 else "assistance.learning_diary_hint.operation.message_usage_second_hint_last_learning_diary")
        else:
            return None

        return AssistanceResult(
            assistance=[
                Assistance.create_with_default_parameters(
                    user_id=user_id,
                    assistance_objects=[AssistanceObject.create_with_default_parameters(
                        user_id=user_id,
                        parameters=[
                            AssistanceParameter.create_with_default_parameters(
                                key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                                value=message,
                            )
                        ],
                    )],
                )
            ]
        )
