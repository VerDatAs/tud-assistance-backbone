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
    ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE, ASSISTANCE_CONTEXT_PARAMETER_KEY_A_ID, ASSISTANCE_OBJECT_PARAMETER_KEY_URI,
    SubsequentAssistanceOperation, SubsequentAssistanceOperationType,
)
from service.db.assistance import read_assistance_by_a_id
from service.db.statement import read_statement_by_id
from service.db.student_model import read_student_model_by_user_id
from service.i18n import t, LOCALE_IDENTIFIER_DE
from service.statement import get_user_id


class GreetingAssistance(ReactiveAssistanceProcess):
    TOOLCHECK_SCREENCAST_HINT_OPERATION_KEY = "screencast_hint_operation"

    @staticmethod
    def get_key() -> str:
        return "greeting"

    def __init__(self) -> None:
        super().__init__()
        self._register_operation(
            ASSISTANCE_OPERATION_KEY_INITIATION,
            GreetingAssistanceInitiationOperation(
                assistance_process=self,
                target_status=AssistanceStateStatus.COMPLETED,
            ),
        )
        self._register_operation(
            self.TOOLCHECK_SCREENCAST_HINT_OPERATION_KEY,
            ToolcheckScreencastHintOperation(
                assistance_process=self,
                target_status=AssistanceStateStatus.COMPLETED,
                subsequent_operations=[],
                assistance_in_progress_required=True,
                delete_scheduled_operations=True,
                send_state_update_to_related_users=False
            ),
        )


class GreetingAssistanceInitiationOperation(AssistanceOperation):
    def is_applicable(self, ctx: AssistanceContext) -> bool:
        try:
            statement = read_statement_by_id(
                ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_STATEMENT_ID)
            )
            if statement is None:
                return False
            return statement.verb.id == StatementVerbId.LOGGED_IN.value
        except (AssistanceParameterException | AttributeError):
            return False

    def _execute(self, ctx: AssistanceContext) -> AssistanceResult | None:
        user_id = get_user_id(
            read_statement_by_id(
                ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_STATEMENT_ID)
            )
        )
        student_model = read_student_model_by_user_id(user_id=user_id)
        if student_model is None:
            raise StudentModelNotExistsError()
        if student_model.experiences is None or len(student_model.experiences) <= 1:
            message = t(LOCALE_IDENTIFIER_DE, "assistance.greeting.operation.greeting")
            self.target_status = AssistanceStateStatus.IN_PROGRESS
            self.subsequent_operations = [
                SubsequentAssistanceOperation(
                    type=SubsequentAssistanceOperationType.SCHEDULED_OPERATION,
                    operation_key=GreetingAssistance.TOOLCHECK_SCREENCAST_HINT_OPERATION_KEY,
                    time_to_invocation_in_s=5
                )
            ]
        else:
            message = t(LOCALE_IDENTIFIER_DE, "assistance.greeting.operation.welcome_back")

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


class ToolcheckScreencastHintOperation(AssistanceOperation):
    def post_init(self):
        self.assistance_in_progress_required = True

    def _execute(self, ctx: AssistanceContext) -> AssistanceResult | None:
        assistance = read_assistance_by_a_id(
            ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_A_ID)
        )
        assistance.assistance_objects = [
            AssistanceObject.create_with_default_parameters(
                user_id=assistance.user_id,
                parameters=[
                    AssistanceParameter.create_with_default_parameters(
                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
                        value=t(LOCALE_IDENTIFIER_DE, "assistance.greeting.operation.toolcheck_screencast_hint"),
                    ),
                    AssistanceParameter.create_with_default_parameters(
                        key=ASSISTANCE_OBJECT_PARAMETER_KEY_URI,
                        value="https://youtu.be/AJPM0PD0kx4",
                    )
                ],
            )
        ]
        return AssistanceResult(assistance=[assistance])
