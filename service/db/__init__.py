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

from functools import lru_cache
from typing import Any, Mapping, List, Callable

import pymongo
from loguru import logger
from pymongo.database import Database

from model.core.dot_dict import DotDict
from model.core.tutorial_module import AssistanceParameterSearchCriteria
from service.environment import (
    mongo_host,
    mongo_port,
    mongo_database,
    mongo_transactions_supported,
    mongo_replica_set,
)

ASSISTANCE_COLLECTION_NAME = "assistance"
ASSISTANCE_OBJECTS_COLLECTION_NAME = "assistance_objects"
ASSISTANCE_OPERATIONS_COLLECTION_NAME = "assistance_operations"
EXPERIENCES_COLLECTION_NAME = "experiences"
LEARNING_CONTENT_OBJECTS_COLLECTION_NAME = "learning_content_objects"
LEARNING_CONTENT_OBJECT_MODELS_COLLECTION_NAME = "learning_content_object_models"
SETTINGS_COLLECTION_NAME = "settings"
STATEMENT_SIMULATIONS_COLLECTION_NAME = "statement_simulations"
STATEMENTS_COLLECTION_NAME = "statements"
STUDENT_MODELS_COLLECTION_NAME = "student_models"


@lru_cache
def get_mongo_client() -> pymongo.MongoClient:
    mongo_client = pymongo.MongoClient(
        host=mongo_host(), port=mongo_port(), replicaSet=mongo_replica_set()
    )
    logger.info(f"Connect to MongoDB {mongo_host()}:{mongo_port()}.")
    return mongo_client


@lru_cache
def get_mongo_db_client(
        mongo_client: pymongo.MongoClient | None = None,
) -> Database[Mapping[str, Any] | Any]:
    return (get_mongo_client() if mongo_client is None else mongo_client)[
        mongo_database()
    ]


def execute_mongo_operation_in_transaction(operation):
    if mongo_transactions_supported():
        mongo_client = get_mongo_client()
        client = get_mongo_db_client(mongo_client)
        with mongo_client.start_session() as session:
            with session.start_transaction():
                return operation(client, session)
    else:
        return operation(get_mongo_db_client(), None)


def disconnect_mongo_client() -> None:
    get_mongo_client().close()
    logger.info("Disconnected from MongoDB.")


def read_collection_documents(
        collection_name: str,
        mongo_filer: dict = None,
        mongo_projection: dict = None,
        objects_per_page: int = None,
        page: int = None,
        document_processing_function: Callable = lambda document: DotDict(document)
):
    client = get_mongo_db_client()
    find_filter = mongo_filer if mongo_filer is not None else {}
    projection = mongo_projection if mongo_projection is not None else {}

    logger.trace(f"Read collection documents using filter {find_filter}")

    if page is not None and objects_per_page is not None:
        find_result = (
            client[collection_name]
            .find(filter=find_filter, projection=projection)
            .skip((page - 1) * objects_per_page)
            .limit(objects_per_page)
        )
    elif page is None and objects_per_page is None:
        find_result = client[collection_name].find(filter=find_filter, projection=projection)
    elif page is None and objects_per_page is not None:
        find_result = (
            client[collection_name]
            .find(filter=find_filter, projection=projection)
            .limit(objects_per_page)
        )
    else:
        raise ValueError("Missing number of objects per page for paging!")

    return list(map(document_processing_function, find_result))


def create_mongo_filter_from_search_criteria(
        attribute_search_keywords: dict,
        search_criterias: List[AssistanceParameterSearchCriteria],
):
    def create_mongo_filter_attribute(
            search_criteria: AssistanceParameterSearchCriteria,
    ) -> dict:
        if search_criteria.key in attribute_search_keywords.keys():
            return {
                attribute_search_keywords[search_criteria.key]: search_criteria.value
            }
        else:
            return {
                "$and": [
                    {"parameters.key": {"$eq": search_criteria.key}},
                    {"parameters.value": {"$eq": search_criteria.value}},
                ]
            }

    if len(search_criterias) == 0:
        mongo_filter = {}
    elif len(search_criterias) == 1:
        mongo_filter = create_mongo_filter_attribute(search_criterias[0])
    else:
        mongo_filter_list = []
        for search_criteria in search_criterias:
            mongo_filter_list.append(create_mongo_filter_attribute(search_criteria))
        mongo_filter = {"$and": mongo_filter_list}
    return mongo_filter
