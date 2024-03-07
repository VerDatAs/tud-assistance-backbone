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
from error.tutorial_module import AssistanceParameterException
from model.core.expert_module import LCO_ATTRIBUTE_KEY_FINAL_TEST_INDICATOR, LearningContentObject
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
    ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE, ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE,
)
from service.db.experience import read_experiences_by_user_id_and_object_id_regexs_and_verb_ids
from service.db.learning_content_object import read_learning_content_object_by_object_id
from service.db.statement import read_statement_by_id
from service.i18n import t, LOCALE_IDENTIFIER_DE
from service.learning_content_object import get_learning_content_object_attribute_value, get_root_lco, \
    get_sub_learning_content_objects
from service.statement import get_user_id, ilias_statement_h5p_object_id_mongo_regex_without_sub_content_id


class FinalTestFeedbackAssistance(ReactiveAssistanceProcess):
    @staticmethod
    def get_key() -> str:
        return "final_test_feedback"

    def __init__(self) -> None:
        super().__init__()
        self._register_operation(
            ASSISTANCE_OPERATION_KEY_INITIATION,
            FinalTestFeedbackAssistanceInitiationOperation(
                assistance_process=self,
                target_status=AssistanceStateStatus.COMPLETED,
            ),
        )


class FinalTestFeedbackAssistanceInitiationOperation(AssistanceOperation):
    CHAPTER_TYPE = "ILIAS_CHAPTER"
    CONTENT_PAGE_TYPE = "ILIAS_CONTENT_PAGE"
    INTERACTIVE_TASK_TYPE = "ILIAS_INTERACTIVE_TASK"

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
            final_test_contained_on_page = False
            for attribute in lco.attributes:
                if type(attribute.value) is LearningContentObject:
                    if attribute.value.lco_type == self.INTERACTIVE_TASK_TYPE:
                        final_test_indicator_attribute_value = get_learning_content_object_attribute_value(
                            lco=attribute.value, lco_attribute_key=LCO_ATTRIBUTE_KEY_FINAL_TEST_INDICATOR)
                        if final_test_indicator_attribute_value is not None and final_test_indicator_attribute_value is True:
                            final_test_contained_on_page = True
                elif type(attribute.value) is list:
                    for value_element in attribute.value:
                        if type(value_element) is LearningContentObject:
                            if value_element.lco_type == self.INTERACTIVE_TASK_TYPE:
                                final_test_indicator_attribute_value = get_learning_content_object_attribute_value(
                                    lco=value_element, lco_attribute_key=LCO_ATTRIBUTE_KEY_FINAL_TEST_INDICATOR)
                                if final_test_indicator_attribute_value is not None and final_test_indicator_attribute_value is True:
                                    final_test_contained_on_page = True
                        if final_test_contained_on_page:
                            break
                if final_test_contained_on_page:
                    break
            return final_test_contained_on_page
        except (AssistanceParameterException | AttributeError):
            return False

    def _execute(self, ctx: AssistanceContext) -> AssistanceResult | None:
        statement = read_statement_by_id(ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_STATEMENT_ID))
        user_id = get_user_id(
            statement
        )

        object_id = statement.object.id
        lco = read_learning_content_object_by_object_id(object_id)
        root_lco = get_root_lco(lco)
        sub_chapter_lcos = list(filter(lambda sub_lco: sub_lco.lco_type == self.CHAPTER_TYPE,
                                       get_sub_learning_content_objects(root_lco)))

        referenced_tasks = []
        lco = read_learning_content_object_by_object_id(statement.object.id)
        for attribute in lco.attributes:
            if type(attribute.value) is LearningContentObject and attribute.value.lco_type == self.INTERACTIVE_TASK_TYPE:
                referenced_tasks.append(attribute.value)
            elif type(attribute.value) is list:
                for value_element in attribute.value:
                    if type(value_element) is LearningContentObject and value_element.lco_type == self.INTERACTIVE_TASK_TYPE:
                        referenced_tasks.append(value_element)
        referenced_task_object_ids = [task_lco.object_id for task_lco in referenced_tasks]

        if len(referenced_tasks) == 0:
            logger.warning(f"Analyzed root LCO that should but does not contain interactive tasks!")
            return None

        is_applicable = False
        for chapter_lco in sub_chapter_lcos:
            sub_interactive_task_lcos = list(filter(
                lambda sub_lco: sub_lco.lco_type == self.INTERACTIVE_TASK_TYPE
                                and sub_lco.object_id not in referenced_task_object_ids,
                get_sub_learning_content_objects(chapter_lco)))
            if len(sub_interactive_task_lcos) == 0:
                continue
            task_experiences = read_experiences_by_user_id_and_object_id_regexs_and_verb_ids(
                user_id=user_id,
                object_id_regexs=[
                    ilias_statement_h5p_object_id_mongo_regex_without_sub_content_id(sub_interactive_task_lco.object_id)
                    for sub_interactive_task_lco in sub_interactive_task_lcos],
                verb_ids=[StatementVerbId.ANSWERED.value, StatementVerbId.COMPLETED.value])
            if len(task_experiences) == 0:
                logger.debug(f"No experiences for interactive tasks of {chapter_lco.lco_id}")
                is_applicable = True
                break

        if not is_applicable:
            return None

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
                                    value=t(LOCALE_IDENTIFIER_DE,
                                            "assistance.final_test_feedback.operation.message_not_enough_tasks_solved_part1"),
                                )
                            ],
                        ),
                        AssistanceObject.create_with_default_parameters(
                            user_id=user_id,
                            parameters=[
                                AssistanceParameter.create_with_default_parameters(
                                    key=ASSISTANCE_OBJECT_PARAMETER_KEY_SYSTEM_MESSAGE,
                                    value=t(LOCALE_IDENTIFIER_DE,
                                            "assistance.final_test_feedback.operation.system_message_not_enough_tasks_solved_part2"),
                                )
                            ],
                        ),
                    ],
                )
            ]
        )
