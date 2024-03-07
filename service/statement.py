"""
    Assistance Backbone for the assistance system developed as part of the VerDatAs project
    Copyright (C) 2022-2024 TU Dresden (Niklas Harbig, Sebastian Kucharski)

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

import asyncio
import re

from loguru import logger

from model.api.statement import Statement as StatementSchema
from model.core.student_module import Statement, Experience, StatementVerbId
from service.datetime import current_datetime
from service.db.experience import create_experience
from service.db.learning_content_object import read_learning_content_objects_by_object_id
from service.db.statement import create_statement
from service.db.student_model import read_or_create_student_model_by_user_id, update_student_model_online_by_user_id
from service.stomp import stomp_server, STOMP_SUBSCRIPTION_DESTINATION_STATEMENT


def get_user_id(statement: Statement) -> str:
    user_id = statement.actor.account.name
    if user_id is None:
        raise AttributeError(f"Statement {statement.id} is not related to any user!")
    return user_id


def ilias_statement_references_course(object_id: str) -> bool:
    match = re.search(r".*target=(.*?)_.*", object_id)
    if match is None:
        return False
    return match.group(1) == "crs"


def ilias_statement_references_h5p_content(object_id: str) -> bool:
    match = re.search(r".*h5p_object_id=.*", object_id)
    return match is not None


def ilias_statement_h5p_object_id_without_sub_content_id(object_id: str) -> str:
    match = re.search(r"(.*)(&h5p-subContentId=.*?)(&.*)", object_id)
    if match is None:
        return object_id
    if len(match.groups()) == 3:
        return f"{match.group(1)}{match.group(3)}"
    elif len(match.groups()) == 2:
        return match.group(1)
    else:
        raise SystemError()


def ilias_statement_h5p_object_id_mongo_regex_without_sub_content_id(object_id: str) -> str:
    match = re.search(r"(.*h5p_object_id=\d*)(&h5p-subContentId=.*?)?(&.*)?", object_id)
    if match is None:
        mongo_regex = object_id
    elif len(match.groups()) == 3:
        mongo_regex = f"{match.group(1)}&h5p-subContentId=.*{'' if match.group(3) is None else match.group(3)}"
    else:
        raise SystemError()
    return mongo_regex.replace("?", "\\?")


def process_statement(statement: Statement) -> None:
    create_statement(statement)

    asyncio.create_task(
        stomp_server.send_message(STOMP_SUBSCRIPTION_DESTINATION_STATEMENT,
                                  StatementSchema.model_validate(statement.to_dict()).model_dump_json(by_alias=True)))
    asyncio.create_task(
        stomp_server.send_message(f"{STOMP_SUBSCRIPTION_DESTINATION_STATEMENT}/{get_user_id(statement)}",
                                  StatementSchema.model_validate(statement.to_dict()).model_dump_json(by_alias=True)))

    if statement.verb.id == StatementVerbId.ASSISTED.value:
        return

    user_id = get_user_id(statement)

    object_id = statement.object.id
    read_or_create_student_model_by_user_id(user_id, False)

    if statement.verb.id == StatementVerbId.LOGGED_OUT.value:
        update_student_model_online_by_user_id(user_id, False)
    else:
        update_student_model_online_by_user_id(user_id, True)

    experience = Experience.create_with_default_parameters(
        timestamp=current_datetime(),
        statement_id=statement.id,
        object_id=object_id,
        verb_id=statement.verb.id)

    # TODO: Process LCO recursively bottom-up?
    lcos = read_learning_content_objects_by_object_id(ilias_statement_h5p_object_id_without_sub_content_id(object_id),
                                                      False)
    if lcos is None or not lcos:
        logger.info("Statement for unknown LCO received")
    elif len(lcos) != 1:
        logger.info("ObjectId of the received statement applies to more than one LCO")
    else:
        experience.lco_id = lcos[0].lco_id

    if StatementVerbId.ANSWERED.value == statement.verb.id or StatementVerbId.COMPLETED.value == statement.verb.id:
        experience.result = statement.result

    create_experience(experience, user_id)
