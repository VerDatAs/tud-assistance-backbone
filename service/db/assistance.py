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

import uuid
from typing import List

from error.tutorial_module import AssistanceNotExistsException, CompletedAssistanceModifyException
from model.core import ModelList
from model.core.tutorial_module import (
    Assistance,
    AssistanceParameterSearchCriteria,
    AssistanceStateStatus, AssistanceObject,
)
from service.datetime import current_datetime
from service.db import (
    get_mongo_db_client,
    ASSISTANCE_COLLECTION_NAME,
    read_collection_documents,
    create_mongo_filter_from_search_criteria, ASSISTANCE_OBJECTS_COLLECTION_NAME,
)
from service.db.assistance_object import create_assistance_objects


def create_assistance(assistance: Assistance) -> Assistance:
    assistance.a_id = str(uuid.uuid4())
    assistance.timestamp = current_datetime()

    assistance.assistance_objects = [] if assistance.assistance_objects is None or len(
        assistance.assistance_objects) == 0 else [
        {"_id": created_ao._id} for created_ao in
        create_assistance_objects(assistance.assistance_objects, assistance.a_id)]

    assistance_dict = assistance.to_dict()
    get_mongo_db_client()[ASSISTANCE_COLLECTION_NAME].insert_one(
        assistance_dict
    )

    return __load_assistance_objects(assistance_dict)


def read_assistance(page: int = None, objects_per_page: int = None) -> ModelList:
    assistance = read_collection_documents(
        collection_name=ASSISTANCE_COLLECTION_NAME,
        objects_per_page=objects_per_page,
        page=page,
        document_processing_function=__load_assistance_objects
    )

    return ModelList(
        model_list=assistance,
        model_list_name="assistanceRecords",
        total_number_of_models=get_mongo_db_client()[
            ASSISTANCE_COLLECTION_NAME
        ].count_documents({}),
        provided_number_of_models=len(assistance),
        page_number=page,
    )


def read_assistance_by_a_id(a_id: str) -> Assistance | None:
    find_one_result = get_mongo_db_client()[ASSISTANCE_COLLECTION_NAME].find_one({"a_id": a_id})

    if find_one_result is None:
        return None

    return __load_assistance_objects(find_one_result)


def read_assistance_by_search_criteria(
        search_criterias: List[AssistanceParameterSearchCriteria],
        page: int = None,
        objects_per_page: int = None,
) -> ModelList:
    attribute_search_keywords = {
        "aId": "a_id",
        "userId": "user_id",
        "timestamp": "timestamp",
        "typeKey": "type_key",
    }

    mongo_filter = create_mongo_filter_from_search_criteria(
        attribute_search_keywords, search_criterias
    )

    assistance = read_collection_documents(
        ASSISTANCE_COLLECTION_NAME,
        mongo_filer=mongo_filter,
        objects_per_page=objects_per_page,
        page=page,
        document_processing_function=__load_assistance_objects
    )

    return ModelList(
        model_list=assistance,
        model_list_name="assistanceRecords",
        total_number_of_models=get_mongo_db_client()[
            ASSISTANCE_COLLECTION_NAME
        ].count_documents(mongo_filter),
        provided_number_of_models=len(assistance),
        page_number=page,
    )


def read_assistance_by_user_id_and_type_keys_and_status(
        user_id: str, type_keys: List[str], possible_states: List[AssistanceStateStatus]) -> List[Assistance]:
    mongo_filter_and_condition = [
        {"type_key": {"$in": type_keys}},
        {"user_id": user_id}
    ]
    if len(possible_states) == 1:
        mongo_filter_and_condition.append({"assistance_state.status": possible_states[0].value})
    elif len(possible_states) > 1:
        mongo_filter_and_condition.append({
            "$or": [{"assistance_state.status": possible_state.value} for possible_state in possible_states]
        })
    mongo_filter = {
        "$and": mongo_filter_and_condition
    }
    return read_collection_documents(
        ASSISTANCE_COLLECTION_NAME,
        mongo_filer=mongo_filter,
        document_processing_function=__load_assistance_objects
    )


def read_assistance_by_related_user_id_and_type_keys_and_status(
        user_id: str, type_keys: List[str], possible_states: List[AssistanceStateStatus]) -> List[Assistance]:
    mongo_filter_and_condition = [
        {"type_key": {"$in": type_keys}},
        {"parameters": {"$elemMatch": {"key": "related_user_ids", "value": {"$eq": user_id}}}}
    ]
    if len(possible_states) == 1:
        mongo_filter_and_condition.append({"assistance_state.status": possible_states[0].value})
    elif len(possible_states) > 1:
        mongo_filter_and_condition.append({
            "$or": [{"assistance_state.status": possible_state.value} for possible_state in possible_states]
        })
    mongo_filter = {
        "$and": mongo_filter_and_condition
    }
    return read_collection_documents(
        ASSISTANCE_COLLECTION_NAME,
        mongo_filer=mongo_filter,
        document_processing_function=__load_assistance_objects
    )


def read_assistance_by_status(
        possible_states: List[AssistanceStateStatus],
) -> List[Assistance]:
    if len(possible_states) == 0:
        return []
    elif len(possible_states) == 1:
        mongo_filter = {"assistance_state.status": possible_states[0].value}
    else:
        mongo_filter = {
            "$or": list(
                map(
                    lambda possible_state: {
                        "assistance_state.status": possible_state.value
                    },
                    possible_states,
                )
            )
        }

    assistance_list = read_collection_documents(
        collection_name=ASSISTANCE_COLLECTION_NAME, mongo_filer=mongo_filter,
        document_processing_function=__load_assistance_objects
    )

    return list(
        map(lambda assistance: Assistance(assistance.to_dict()), assistance_list)
    )


def update_assistance_adding_assistance_objects(
        assistance: Assistance,
) -> Assistance:
    client = get_mongo_db_client()
    find_one_result = client[ASSISTANCE_COLLECTION_NAME].find_one(
        {"a_id": assistance.a_id}
    )
    if find_one_result is None:
        raise AssistanceNotExistsException()

    existing_assistance = Assistance(find_one_result)
    if (existing_assistance.assistance_state.status == AssistanceStateStatus.COMPLETED
            or existing_assistance.assistance_state.status == AssistanceStateStatus.ABORTED):
        raise CompletedAssistanceModifyException()

    if assistance.assistance_objects is not None and len(assistance.assistance_objects) != 0:
        assistance.assistance_objects = existing_assistance.assistance_objects + [
            {"_id": created_ao._id} for created_ao in
            create_assistance_objects(assistance.assistance_objects, existing_assistance.a_id)]
    else:
        assistance.assistance_objects = existing_assistance.assistance_objects

    assistance_dict = assistance.to_dict()
    get_mongo_db_client()[ASSISTANCE_COLLECTION_NAME].replace_one(
        {"a_id": assistance.a_id}, assistance_dict
    )

    return __load_assistance_objects(assistance_dict)


def update_assistance_by_a_id_adding_assistance_objects(a_id: str,
                                                        assistance_objects: List[AssistanceObject]) -> Assistance:
    client = get_mongo_db_client()
    find_one_result = client[ASSISTANCE_COLLECTION_NAME].find_one(
        {"a_id": a_id}
    )
    if find_one_result is None:
        raise AssistanceNotExistsException()

    existing_assistance = Assistance(find_one_result)
    if existing_assistance.assistance_state.status == AssistanceStateStatus.COMPLETED or existing_assistance.assistance_state.status == AssistanceStateStatus.ABORTED:
        raise CompletedAssistanceModifyException()

    existing_assistance.assistance_objects += [
        {"_id": created_ao._id} for created_ao in
        create_assistance_objects(assistance_objects, existing_assistance.a_id)]

    assistance_dict = existing_assistance.to_dict()
    get_mongo_db_client()[ASSISTANCE_COLLECTION_NAME].replace_one(
        {"a_id": existing_assistance.a_id}, assistance_dict
    )

    return __load_assistance_objects(assistance_dict)


def update_assistance_by_a_id_reset_next_operation_keys(a_id: str):
    get_mongo_db_client()[ASSISTANCE_COLLECTION_NAME].update_one(
        filter={"a_id": a_id}, update={"$set": {"next_operation_keys": []}}
    )


def __load_assistance_objects(assistance: dict) -> Assistance:
    if "assistance_objects" not in assistance or (not assistance.get("assistance_objects")):
        return Assistance(assistance)
    assistance["assistance_objects"] = get_mongo_db_client()[ASSISTANCE_OBJECTS_COLLECTION_NAME].find({
        "_id": {"$in": list(map(lambda ao_ref: ao_ref.get("_id"), assistance.get("assistance_objects")))}
    })
    return Assistance(assistance)
