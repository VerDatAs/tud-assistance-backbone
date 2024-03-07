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
    ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE, ASSISTANCE_OBJECT_PARAMETER_KEY_URI, SubsequentAssistanceOperation,
    SubsequentAssistanceOperationType, ASSISTANCE_CONTEXT_PARAMETER_KEY_A_ID,
    ASSISTANCE_CONTEXT_PARAMETER_KEY_ASSISTANCE_OBJECTS, ASSISTANCE_OBJECT_PARAMETER_KEY_REQUIRE_CLICK_NOTIFICATION,
    ASSISTANCE_OBJECT_PARAMETER_KEY_CLICK_NOTIFICATION_RESPONSE,
)
from service.db.assistance import read_assistance_by_a_id
from service.db.experience import read_experiences_by_user_id_and_object_ids_and_verb_id, \
    read_experiences_by_user_id_and_object_ids
from service.db.learning_content_object import read_learning_content_object_by_object_id
from service.db.statement import read_statement_by_id
from service.i18n import t, LOCALE_IDENTIFIER_DE
from service.learning_content_object import get_root_lco, \
    get_sub_learning_content_objects, get_learning_content_object_attribute_value, \
    get_sub_learning_content_object_object_ids
from service.statement import get_user_id


class ToolCheckHintAssistance(ReactiveAssistanceProcess):
    ASSISTANCE_PARAMETER_KEY_EXPERIENCED_LCO_OBJECT_ID = "experienced_lco_object_id"

    @staticmethod
    def get_key() -> str:
        return "tool_check_hint"

    def __init__(self) -> None:
        super().__init__()

        provide_usage_hint_operation_key = "provide_usage_hint"

        self._register_operation(
            ASSISTANCE_OPERATION_KEY_INITIATION,
            ToolCheckAssistanceInitiationOperation(
                assistance_process=self,
                target_status=AssistanceStateStatus.IN_PROGRESS,
                subsequent_operations=[
                    SubsequentAssistanceOperation(
                        type=SubsequentAssistanceOperationType.TRIGGERED_OPERATION,
                        operation_key=provide_usage_hint_operation_key,
                    ),
                ],
            ),
        )

        self._register_operation(
            provide_usage_hint_operation_key,
            ProvideUsageHintOperation(
                assistance_process=self,
                target_status=AssistanceStateStatus.COMPLETED,
                subsequent_operations=[],
            ),
        )


class ToolCheckAssistanceInitiationOperation(AssistanceOperation):
    CONTENT_PAGE_TYPE = "ILIAS_CONTENT_PAGE"
    LCO_ATTRIBUTE_KEY_LECTURER_DASHBOARD_LINK = "lecturerDashboardLink"

    def is_applicable(self, ctx: AssistanceContext) -> bool:
        try:
            statement = read_statement_by_id(
                ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_STATEMENT_ID)
            )
            if statement is None or statement.verb.id != StatementVerbId.EXPERIENCED.value:
                return False
            lco = read_learning_content_object_by_object_id(statement.object.id)
            if lco is None or lco.lco_type != self.CONTENT_PAGE_TYPE:
                return False
            sub_lcos = list(filter(lambda sub_lco: sub_lco.lco_type == self.CONTENT_PAGE_TYPE,
                                   get_sub_learning_content_objects(get_root_lco(lco))))

            if len(read_experiences_by_user_id_and_object_ids_and_verb_id(
                    user_id=get_user_id(statement),
                    object_ids=[sub_lco.object_id for sub_lco in sub_lcos],
                    verb_id=StatementVerbId.EXPERIENCED.value
            )) == 10:
                return True
        except (AssistanceParameterException | AttributeError):
            return False
        return False

    def _execute(self, ctx: AssistanceContext) -> AssistanceResult | None:
        statement = read_statement_by_id(ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_STATEMENT_ID))
        user_id = get_user_id(statement)
        root_lco = get_root_lco(read_learning_content_object_by_object_id(statement.object.id))

        lecturer_dashboard_link = get_learning_content_object_attribute_value(
            lco=root_lco, lco_attribute_key=self.LCO_ATTRIBUTE_KEY_LECTURER_DASHBOARD_LINK)
        if lecturer_dashboard_link is None:
            return None

        assistance = Assistance.create_with_default_parameters(
            user_id=user_id,
            assistance_objects=[
                AssistanceObject.create_with_default_parameters(
                    user_id=user_id,
                    parameters=[
                        AssistanceParameter.create_with_default_parameters(
                            key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                            value=t(LOCALE_IDENTIFIER_DE,
                                    "assistance.tool_check_hint.operation.message_hint_for_perspective_change"),
                        ),
                        AssistanceParameter.create_with_default_parameters(
                            key=ASSISTANCE_OBJECT_PARAMETER_KEY_URI,
                            value=lecturer_dashboard_link,
                        ),
                        AssistanceParameter.create_with_default_parameters(
                            key=ASSISTANCE_OBJECT_PARAMETER_KEY_REQUIRE_CLICK_NOTIFICATION,
                            value=1,
                        ),
                    ],
                )
            ],
        )
        assistance.parameters = [
            AssistanceParameter.create_with_default_parameters(
                ToolCheckHintAssistance.ASSISTANCE_PARAMETER_KEY_EXPERIENCED_LCO_OBJECT_ID,
                statement.object.id,
            ),
        ]

        return AssistanceResult(assistance=[assistance])


class ProvideUsageHintOperation(AssistanceOperation):
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
                                                          ASSISTANCE_OBJECT_PARAMETER_KEY_CLICK_NOTIFICATION_RESPONSE)
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

        object_id = get_first_assistance_parameter_by_key(
            assistance.parameters,
            ToolCheckHintAssistance.ASSISTANCE_PARAMETER_KEY_EXPERIENCED_LCO_OBJECT_ID,
        ).value
        root_lco = get_root_lco(read_learning_content_object_by_object_id(object_id))
        sub_lco_experiences = sorted(read_experiences_by_user_id_and_object_ids(
            user_id=assistance.user_id, object_ids=get_sub_learning_content_object_object_ids(root_lco)),
            key=lambda sub_lco_experience: sub_lco_experience.timestamp, reverse=True)

        assistance.assistance_objects = [
            AssistanceObject.create_with_default_parameters(
                user_id=assistance.user_id,
                parameters=[
                    AssistanceParameter.create_with_default_parameters(
                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                        value=t(LOCALE_IDENTIFIER_DE,
                                'assistance.tool_check_hint.operation.message_usage_hint'),
                    )
                ]
            ),
            AssistanceObject.create_with_default_parameters(
                user_id=assistance.user_id,
                parameters=[
                    AssistanceParameter.create_with_default_parameters(
                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                        value=t(LOCALE_IDENTIFIER_DE,
                                'assistance.tool_check_hint.operation.message_go_back_hint'),
                    ),
                    AssistanceParameter.create_with_default_parameters(
                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_URI,
                        value=sub_lco_experiences[0].object_id,
                    )
                ],
            )
        ]
        return AssistanceResult(assistance=[assistance])
