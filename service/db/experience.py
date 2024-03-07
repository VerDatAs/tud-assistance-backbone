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

from typing import List

from loguru import logger

from model.core import DotDict
from model.core.student_module import Experience
from service.db import get_mongo_db_client, EXPERIENCES_COLLECTION_NAME, STUDENT_MODELS_COLLECTION_NAME


def create_experience(experience: Experience, user_id: str) -> Experience:
    experience.user_id = user_id
    experience_dict = experience.to_dict()
    insert_one_result = get_mongo_db_client()[EXPERIENCES_COLLECTION_NAME].insert_one(experience_dict)
    inserted_experience = DotDict()
    inserted_experience._id = insert_one_result.inserted_id
    get_mongo_db_client()[STUDENT_MODELS_COLLECTION_NAME].update_one(
        {"user_id": user_id}, {"$push": {"experiences": inserted_experience.to_dict()}})
    return Experience(experience_dict)


def create_experience_objects(experiences: List[Experience], user_id: str) -> List[Experience]:
    experience_object_dicts = []
    for experience in experiences:
        experience.user_id = user_id
        experience_object_dicts.append(experience.to_dict())

    get_mongo_db_client()[EXPERIENCES_COLLECTION_NAME].insert_many(
        experience_object_dicts
    )

    return list(map(lambda e: Experience(e), experience_object_dicts))


def read_experiences_by_user_id_and_lco_ids_and_verb_ids(
        user_id: str, lco_ids: List[str], verb_ids: List[str]) -> List[Experience]:
    and_expression = [{"user_id": user_id}]
    if len(lco_ids) != 0:
        and_expression.append({"$or": [{"lco_id": lco_id} for lco_id in lco_ids]})
    if len(verb_ids) != 0:
        and_expression.append({"$or": [{"verb_id": verb_id} for verb_id in verb_ids]})
    mongo_filter = {"$and": and_expression}
    logger.debug(mongo_filter)
    experiences_dicts = get_mongo_db_client()[EXPERIENCES_COLLECTION_NAME].find(mongo_filter)
    return [Experience(experiences_dict) for experiences_dict in experiences_dicts]


def read_experiences_by_user_id_and_object_id_regexs_and_verb_ids(
        user_id: str, object_id_regexs: List[str], verb_ids: List[str]) -> List[Experience]:
    and_expression = [{"user_id": user_id}]
    if len(object_id_regexs) != 0:
        and_expression.append(
            {"$or": [{"object_id": {"$regex": object_id_regex}} for object_id_regex in object_id_regexs]})
    if len(verb_ids) != 0:
        and_expression.append({"$or": [{"verb_id": verb_id} for verb_id in verb_ids]})
    mongo_filter = {"$and": and_expression}
    logger.debug(mongo_filter)
    experiences_dicts = get_mongo_db_client()[EXPERIENCES_COLLECTION_NAME].find(mongo_filter)
    return [Experience(experiences_dict) for experiences_dict in experiences_dicts]


def read_experiences_by_object_id_and_verb_id(
        object_id: str, verb_id: str) -> List[Experience]:
    experiences_dicts = get_mongo_db_client()[EXPERIENCES_COLLECTION_NAME].find({
        "$and": [
            {"object_id": object_id},
            {"verb_id": verb_id},
        ]
    })
    return [Experience(experiences_dict) for experiences_dict in experiences_dicts]


def read_experiences_by_user_id_and_object_id_and_verb_id(
        user_id: str, object_id: str, verb_id: str) -> List[Experience]:
    experiences_dicts = get_mongo_db_client()[EXPERIENCES_COLLECTION_NAME].find({
        "$and": [
            {"user_id": user_id},
            {"object_id": object_id},
            {"verb_id": verb_id},
        ]
    })
    return [Experience(experiences_dict) for experiences_dict in experiences_dicts]


def read_experiences_by_user_id_and_object_ids_and_verb_id(
        user_id: str, object_ids: List[str], verb_id: str) -> List[Experience]:
    experiences_dicts = get_mongo_db_client()[EXPERIENCES_COLLECTION_NAME].find({
        "$and": [
            {"user_id": user_id},
            {"$or": [{"object_id": object_id} for object_id in object_ids]},
            {"verb_id": verb_id},
        ]
    })
    return [Experience(experiences_dict) for experiences_dict in experiences_dicts]


def read_experiences_by_user_id_and_object_ids(
        user_id: str, object_ids: List[str]) -> List[Experience]:
    experiences_dicts = get_mongo_db_client()[EXPERIENCES_COLLECTION_NAME].find({
        "$and": [
            {"user_id": user_id},
            {"$or": [{"object_id": object_id} for object_id in object_ids]},
        ]
    })
    return [Experience(experiences_dict) for experiences_dict in experiences_dicts]
