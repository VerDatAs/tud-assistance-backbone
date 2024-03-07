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

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, List

from model.core import GenericModel, parse_data_element, parse_data_list_element, parse_data_bool_element
from model.core.dot_dict import DotDict


class TestEvaluationResult(Enum):
    EXPERT = "expert"
    NO_EXPERT = "no_expert"


class Experience(GenericModel):
    @staticmethod
    def create_with_default_parameters(
            timestamp: datetime, statement_id: str, object_id: str, verb_id: str, result: Any = None
    ) -> Experience:
        experience = Experience()
        experience.timestamp = timestamp
        experience.statement_id = statement_id
        experience.object_id = object_id
        experience.verb_id = verb_id
        experience.result = result
        return experience

    @staticmethod
    def create_with_default_parameters_and_lco_id(
            timestamp: datetime, statement_id: str, object_id: str, verb_id: str, lco_id: str, result: Any = None
    ) -> Experience:
        experience = Experience.create_with_default_parameters(timestamp=timestamp, statement_id=statement_id,
                                                               object_id=object_id, verb_id=verb_id, result=result)
        experience.lco_id = lco_id
        return experience

    def _init(self, data):
        self.timestamp = data.get("timestamp")
        self.statement_id = data.get("statement_id")
        self.object_id = data.get("object_id")
        self.lco_id = data.get("lco_id")
        self.verb_id = data.get("verb_id")
        self.user_id = data.get("user_id")
        self.result = parse_data_element(data=data, key="result",
                                         parse_function=lambda element: DotDict(element) if type(
                                             element) is dict else element)


class ExperienceVerbId(Enum):
    ENTRY_TEST_EVALUATED = "entry_test_evaluated"


class Statement(GenericModel):
    def _init(self, data):
        self.id = data.get("id")
        self.actor = parse_data_element(data=data, key="actor")
        self.object = parse_data_element(data=data, key="object")
        self.verb = parse_data_element(data=data, key="verb")


class StatementSimulation(GenericModel):
    @staticmethod
    def create_with_default_parameters(
            next_statement: Statement, subsequent_statements: List[Statement], supported_assistance_types: List[str],
            time_factor: float, user_id: str | None
    ) -> StatementSimulation:
        statement_simulation = StatementSimulation()
        statement_simulation.next_statement = next_statement
        statement_simulation.subsequent_statements = subsequent_statements
        statement_simulation.supported_assistance_types = supported_assistance_types
        statement_simulation.time_factor = time_factor
        statement_simulation.user_id = user_id
        return statement_simulation

    def _init(self, data):
        self.simulation_id = data.get("simulation_id")
        self.next_statement = Statement(data.get("next_statement"))
        self.subsequent_statements = parse_data_list_element(
            data=data, key="subsequent_statements", parse_function=lambda d: Statement(d), default_value=[])
        self.supported_assistance_types = data.get("supported_assistance_types")
        self.time_factor = data.get("time_factor")
        self.time_of_invocation = data.get("time_of_invocation")
        self.user_id = data.get("user_id")
        self.datetime_to_string = False


class StatementVerbId(Enum):
    ANSWERED = "http://adlnet.gov/expapi/verbs/answered"
    ASSISTED = "https://brindlewaye.com/xAPITerms/verbs/assisted/"
    COMPLETED = "http://adlnet.gov/expapi/verbs/completed"
    EXPERIENCED = "http://adlnet.gov/expapi/verbs/experienced"
    INTERACTED = "http://adlnet.gov/expapi/verbs/interacted"
    LOGGED_IN = "https://brindlewaye.com/xAPITerms/verbs/loggedin/"
    LOGGED_OUT = "https://brindlewaye.com/xAPITerms/verbs/loggedout/"
    READ = "http://adlnet.gov/expapi/verbs/read"
    USED = "http://adlnet.gov/expapi/verbs/used"


class StudentLcoProgress(GenericModel):
    @staticmethod
    def create_with_default_parameters(
            user_id: str,
    ) -> StudentLcoProgress:
        student_lco_progress = StudentLcoProgress()
        student_lco_progress.user_id = user_id
        return student_lco_progress

    def _init(self, data):
        self.user_id = data.get("user_id")
        self.progress = parse_data_list_element(data=data, key="progress", parse_function=lambda d: Experience(d))
        self.sub_lco_progress = parse_data_list_element(data=data, key="sub_lco_progress",
                                                        parse_function=lambda d: StudentModelParameter(d))


class StudentModel(GenericModel):
    @staticmethod
    def create_with_default_parameters(
            user_id: str,
    ) -> StudentModel:
        student_model = StudentModel()
        student_model.user_id = user_id
        return student_model

    def _init(self, data):
        self.user_id = data.get("user_id")
        self.assistance_level = data.get("assistance_level", 10)
        self.cooperativeness = parse_data_bool_element(data=data, key="cooperativeness", default_value=True)
        self.online = parse_data_bool_element(data=data, key="online", default_value=False)
        self.experiences = parse_data_list_element(data=data, key="experiences", parse_function=lambda d: Experience(d))
        self.learning_path_in_progress = parse_data_element(data=data, key="learning_path_in_progress")


class StudentModelParameter(GenericModel):
    @staticmethod
    def create_with_default_parameters(
            key: str, value: any
    ) -> StudentModelParameter:
        student_model_parameter = StudentModelParameter()
        student_model_parameter.key = key
        student_model_parameter.value = value
        return student_model_parameter

    def _init(self, data):
        self.key = data.get("key")
        self.value = parse_data_element(data=data, key="value",
                                        parse_function=lambda d: DotDict(d) if type(d) is dict else d)


class UserRole(Enum):
    ADMIN = "ADMIN"
    ASSISTANCE_PROVIDER = "ASSISTANCE_PROVIDER"
