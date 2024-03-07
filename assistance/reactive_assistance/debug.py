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
from error.tutorial_module import AssistanceParameterException
from model.core.tutorial_module import (
    Assistance,
    AssistanceObject,
    AssistanceParameter,
    AssistanceStateStatus,
)
from model.service.assistance import (
    AssistanceContext,
    AssistanceResult,
    AssistancePhase,
    AssistancePhaseStep,
    ASSISTANCE_CONTEXT_PARAMETER_KEY_A_ID,
    ASSISTANCE_OPERATION_KEY_INITIATION,
    AssistanceOperation,
    ASSISTANCE_CONTEXT_PARAMETER_KEY_STATEMENT_ID,
    ASSISTANCE_OBJECT_PARAMETER_KEY_MESSAGE,
    AssistanceOperationSchedule,
)
from service.db.assistance import read_assistance_by_a_id
from service.db.statement import read_statement_by_id
from service.statement import get_user_id


class DebugAssistance(ReactiveAssistanceProcess):
    @staticmethod
    def get_key() -> str:
        return "debug"

    def __init__(self) -> None:
        super().__init__()
        self._register_phases(
            [
                AssistancePhase(
                    parameters=[
                        AssistanceParameter.create_with_default_parameters(
                            "title", "Debug Start Phase"
                        )
                    ],
                    steps=[
                        AssistancePhaseStep(
                            operation_key=ASSISTANCE_OPERATION_KEY_INITIATION,
                            parameters=[
                                AssistanceParameter.create_with_default_parameters(
                                    "title", "Debug Start Step"
                                )
                            ],
                            operation=DebugAssistanceInitiationOperation(
                                self, AssistanceStateStatus.IN_PROGRESS
                            ),
                        ),
                        AssistancePhaseStep(
                            operation_key="scheduled_step",
                            parameters=[
                                AssistanceParameter.create_with_default_parameters(
                                    "title", "Scheduled Step"
                                )
                            ],
                            operation=DebugAssistanceScheduledOperation(
                                self,
                                AssistanceStateStatus.COMPLETED,
                            ),
                            schedule=AssistanceOperationSchedule(
                                time_to_invocation_in_s=20
                            ),
                        ),
                    ],
                )
            ]
        )


class DebugAssistanceInitiationOperation(AssistanceOperation):
    def is_applicable(self, ctx: AssistanceContext) -> bool:
        try:
            ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_STATEMENT_ID)
            statement = read_statement_by_id(
                ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_STATEMENT_ID)
            )
            if statement is None:
                raise AssistanceParameterException()
            if not get_user_id(statement):
                raise AssistanceParameterException()
        except AssistanceParameterException:
            return False

        return True

    def _execute(self, ctx: AssistanceContext) -> AssistanceResult | None:
        user_id = get_user_id(
            read_statement_by_id(
                ctx.get_parameter(ASSISTANCE_CONTEXT_PARAMETER_KEY_STATEMENT_ID)
            )
        )

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
                                    value=f"Hello {user_id}",
                                )
                            ],
                        )
                    ],
                )
            ]
        )


class DebugAssistanceScheduledOperation(AssistanceOperation):
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
                        value=f"Hello again {assistance.user_id}",
                    )
                ],
            )
        ]
        return AssistanceResult(assistance=[assistance])
