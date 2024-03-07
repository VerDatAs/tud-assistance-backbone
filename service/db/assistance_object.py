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

from model.core import ModelList
from model.core.tutorial_module import (
    AssistanceObject,
    AssistanceParameterSearchCriteria, AssistanceParameter,
)
from service.datetime import current_datetime
from service.db import (
    get_mongo_db_client,
    ASSISTANCE_OBJECTS_COLLECTION_NAME,
    read_collection_documents,
    create_mongo_filter_from_search_criteria,
)


def create_assistance_object(assistance_object: AssistanceObject) -> AssistanceObject:
    assistance_object.ao_id = str(uuid.uuid4())
    assistance_object.timestamp = current_datetime()

    assistance_object_dict = assistance_object.to_dict()
    get_mongo_db_client()[ASSISTANCE_OBJECTS_COLLECTION_NAME].insert_one(
        assistance_object_dict
    )

    return AssistanceObject(assistance_object_dict)


def create_assistance_objects(assistance_objects: List[AssistanceObject], a_id: str) -> List[AssistanceObject]:
    assistance_object_dicts = []
    for assistance_object in assistance_objects:
        assistance_object.a_id = a_id
        assistance_object.ao_id = str(uuid.uuid4())
        assistance_object.timestamp = current_datetime()
        assistance_object_dicts.append(assistance_object.to_dict())

    get_mongo_db_client()[ASSISTANCE_OBJECTS_COLLECTION_NAME].insert_many(
        assistance_object_dicts
    )

    return list(map(lambda ao: AssistanceObject(ao), assistance_object_dicts))


def read_assistance_objects_by_search_criteria(
        search_criterias: List[AssistanceParameterSearchCriteria],
        page: int = None,
        objects_per_page: int = None,
) -> ModelList | None:
    attribute_search_keywords = {
        "aId": "a_id",
        "aoId": "ao_id",
        "userId": "user_id",
        "timestamp": "timestamp",
        "type": "type",
    }

    mongo_filter = create_mongo_filter_from_search_criteria(
        attribute_search_keywords, search_criterias
    )

    assistance_objects = read_collection_documents(
        ASSISTANCE_OBJECTS_COLLECTION_NAME,
        mongo_filer=mongo_filter,
        objects_per_page=objects_per_page,
        page=page,
        document_processing_function=lambda document: AssistanceObject(document)
    )

    return ModelList(
        model_list=assistance_objects,
        model_list_name="assistanceObjectRecords",
        total_number_of_models=get_mongo_db_client()[
            ASSISTANCE_OBJECTS_COLLECTION_NAME
        ].count_documents(mongo_filter),
        provided_number_of_models=len(assistance_objects),
        page_number=page,
    )


def read_assistance_objects_by_user_id_and_parameter(
        user_id: str, parameter: AssistanceParameter) -> List[AssistanceObject]:
    return read_collection_documents(
        ASSISTANCE_OBJECTS_COLLECTION_NAME,
        mongo_filer={
            "$and": [
                {"user_id": user_id},
                {"parameters": {"$elemMatch": {"key": parameter.key, "value": parameter.value}}}
            ]
        },
        document_processing_function=lambda document: AssistanceObject(document)
    )
