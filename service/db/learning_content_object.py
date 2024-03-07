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

from loguru import logger

from error.expert_module import (
    LcoNotExistsError,
    LcoPatchInvalidError, LcoWithObjectIdAlreadyExists,
)
from model.core import DotDict
from model.core import ModelList
from model.core.expert_module import (
    LearningContentObject,
    LearningContentObjectAttribute,
    LearningContentObjectParameterSearchCriteria, LearningContentObjectPatchOperation,
)
from service.datetime import current_datetime
from service.db import (
    read_collection_documents,
    get_mongo_db_client,
    LEARNING_CONTENT_OBJECTS_COLLECTION_NAME,
    execute_mongo_operation_in_transaction,
)

FILTER_ARCHIVED_FALSE_DICT = {
    "$or": [
        {"archived": {"$exists": False}},
        {"archived": False},
    ]
}


def create_learning_content_object(
        preliminary_lco: LearningContentObject, recursive_read: bool = True
) -> LearningContentObject:
    # TODO: Validation?

    if preliminary_lco.object_id is not None and read_learning_content_object_by_object_id(
            preliminary_lco.object_id) is not None:
        raise LcoWithObjectIdAlreadyExists(f"LCO with object ID {preliminary_lco.object_id} already exists!")

    now = current_datetime()

    def operation(client, session):
        def prepare_insert_function(lco_to_insert, parent_lco):
            lco_to_insert.lco_id = str(uuid.uuid4())
            lco_to_insert.updated = now
            lco_to_insert.parent_lco_id = None if parent_lco is None else parent_lco.lco_id
            return lco_to_insert

        def insert_function(lco_to_insert, parent_lco):
            if lco_to_insert.object_id is not None and read_learning_content_object_by_object_id(
                    lco_to_insert.object_id) is not None:
                raise LcoWithObjectIdAlreadyExists(f"LCO with object ID {lco_to_insert.object_id} already exists!")
            insert_one_result = client[LEARNING_CONTENT_OBJECTS_COLLECTION_NAME].insert_one(
                lco_to_insert.to_dict(), session=session
            )
            inserted_lco = DotDict()
            inserted_lco._id = insert_one_result.inserted_id
            return inserted_lco

        return __process_learning_content_object_recursively(
            lco=preliminary_lco,
            parent_lco=None,
            lco_preprocessing_function=prepare_insert_function,
            lco_processing_function=insert_function,
        )

    insert_result = execute_mongo_operation_in_transaction(operation)
    find_one_result = get_mongo_db_client()[LEARNING_CONTENT_OBJECTS_COLLECTION_NAME].find_one(
        {
            "$and": [
                {"_id": insert_result._id},
                FILTER_ARCHIVED_FALSE_DICT,
            ]
        }
    )
    if find_one_result is None:
        raise SystemError()

    return __read_lco_recursively(LearningContentObject(find_one_result),
                                  None) if recursive_read else LearningContentObject(find_one_result)


def delete_learning_content_object_by_lco_id(lco_id: str) -> None:
    find_one_result = get_mongo_db_client()[
        LEARNING_CONTENT_OBJECTS_COLLECTION_NAME
    ].find_one(
        {
            "$and": [
                {"lco_id": lco_id},
                FILTER_ARCHIVED_FALSE_DICT,
            ]
        }
    )
    if find_one_result is None:
        raise LcoNotExistsError()

    now = current_datetime()

    def operation(client, session):
        # TODO: Archive only referenced LCOs and delete the others
        return __process_learning_content_object_recursively(
            lco=LearningContentObject(find_one_result),
            parent_lco=None,
            lco_preprocessing_function=lambda lco, parent_lco: LearningContentObject(client[
                LEARNING_CONTENT_OBJECTS_COLLECTION_NAME].find_one(
                {
                    "$and": [
                        {"_id": lco._id},
                        FILTER_ARCHIVED_FALSE_DICT,
                    ]
                }
            )),
            lco_processing_function=lambda lco, parent_lco: client[
                LEARNING_CONTENT_OBJECTS_COLLECTION_NAME
            ].update_one(
                {
                    "$and": [
                        {"_id": lco._id},
                        FILTER_ARCHIVED_FALSE_DICT,
                    ]
                },
                {
                    "$set": {
                        "archived": True,
                        "updated": now,
                    }
                },
                session=session,
            ),
        )

    execute_mongo_operation_in_transaction(operation)


def patch_learning_content_object(
        lco_id_of_lco_to_patch: str, lco_patches: [LearningContentObject]
) -> LearningContentObject:
    # TODO: Validation?

    lco_to_patch = read_learning_content_object_by_lco_id(lco_id_of_lco_to_patch)

    if lco_to_patch is None:
        raise LcoNotExistsError
    if lco_patches is None or len(lco_patches) == 0:
        return lco_to_patch

    lco_attribute_key_to_patched_lco_attribute_dict = {
        lco_attribute_to_patch.key: lco_attribute_to_patch
        for lco_attribute_to_patch in lco_to_patch.attributes
    }

    for lco_patch in lco_patches:
        if ((lco_patch.operation == LearningContentObjectPatchOperation.DELETE.value
             or lco_patch.operation == LearningContentObjectPatchOperation.UPDATE.value)
                and lco_patch.key not in lco_attribute_key_to_patched_lco_attribute_dict):
            raise LcoPatchInvalidError(
                f"LCO attribute with key '{lco_patch.key}' does not exist. Patch of type '{lco_patch.operation}' can not be applied!"
            )
        if (lco_patch.operation == LearningContentObjectPatchOperation.ADD.value
                and lco_patch.key in lco_attribute_key_to_patched_lco_attribute_dict):
            raise LcoPatchInvalidError(
                f"LCO attribute with key '{lco_patch.key}' already exists and can not be added!"
            )
        if ((lco_patch.operation == LearningContentObjectPatchOperation.ADD.value
             or LearningContentObjectPatchOperation.UPDATE.value)
                and "value" not in lco_patch):
            raise LcoPatchInvalidError(
                f"No value specified for patch of type '{lco_patch.operation}' of LCO attribute with key '{lco_patch.key}'!"
            )

        if lco_patch.operation == LearningContentObjectPatchOperation.DELETE.value:
            lco_attribute_key_to_patched_lco_attribute_dict.pop(lco_patch.key)
        elif lco_patch.operation == "ADD" or lco_patch.operation == "UPDATE":
            lco_attribute_key_to_patched_lco_attribute_dict[lco_patch.key] = {
                "key": lco_patch.key,
                "value": lco_patch.value,
            }

    lco_to_patch.attributes = list(
        map(
            lambda patched_lco_attribute: LearningContentObjectAttribute(
                patched_lco_attribute
            ),
            lco_attribute_key_to_patched_lco_attribute_dict.values(),
        )
    )
    return update_learning_content_object_by_lco_id(
        lco_id_of_lco_to_patch, lco_to_patch
    )


def read_learning_content_objects(
        page: int = None, objects_per_page: int = None, recursive_read: bool = True
) -> ModelList:
    lcos = read_collection_documents(
        LEARNING_CONTENT_OBJECTS_COLLECTION_NAME,
        mongo_filer=FILTER_ARCHIVED_FALSE_DICT,
        objects_per_page=objects_per_page,
        page=page,
        document_processing_function=lambda document: __read_lco_recursively(
            LearningContentObject(document), None) if recursive_read else LearningContentObject(document)
    )
    return ModelList(
        model_list=lcos,
        model_list_name="lcos",
        total_number_of_models=get_mongo_db_client()[
            LEARNING_CONTENT_OBJECTS_COLLECTION_NAME
        ].count_documents(FILTER_ARCHIVED_FALSE_DICT),
        provided_number_of_models=len(lcos),
        page_number=page,
    )


def read_learning_content_objects_by_search_criteria(
        search_criterias: [LearningContentObjectParameterSearchCriteria],
        page: int = None,
        objects_per_page: int = None,
        recursive_read: bool = True
) -> ModelList:
    attribute_search_keywords = {
        "lcoId": "lco_id",
        "lcoType": "lco_type",
        "objectId": "object_id",
    }

    mongo_filter_list = [FILTER_ARCHIVED_FALSE_DICT]

    def create_mongo_filter_attribute(
            search_criteria: LearningContentObjectParameterSearchCriteria,
    ) -> dict:
        if search_criteria.key in attribute_search_keywords.keys():
            return {
                attribute_search_keywords[search_criteria.key]: search_criteria.value
            }
        else:
            return {
                "$and": [
                    {"attributes.key": {"$eq": search_criteria.key}},
                    {"attributes.value": {"$eq": search_criteria.value}},
                ]
            }

    for search_criteria in search_criterias:
        mongo_filter_list.append(create_mongo_filter_attribute(search_criteria))
    mongo_filter = {"$and": mongo_filter_list}

    lcos = read_collection_documents(
        LEARNING_CONTENT_OBJECTS_COLLECTION_NAME,
        mongo_filer=mongo_filter,
        objects_per_page=objects_per_page,
        page=page,
        document_processing_function=lambda document: __read_lco_recursively(
            LearningContentObject(document), None) if recursive_read else LearningContentObject(document)
    )
    return ModelList(
        model_list=lcos,
        model_list_name="lcos",
        total_number_of_models=get_mongo_db_client()[
            LEARNING_CONTENT_OBJECTS_COLLECTION_NAME
        ].count_documents(mongo_filter),
        provided_number_of_models=len(lcos),
        page_number=page,
    )


def read_learning_content_object_by_lco_id(lco_id: str, recursive_read: bool = True) -> LearningContentObject | None:
    find_one_result = get_mongo_db_client()[LEARNING_CONTENT_OBJECTS_COLLECTION_NAME].find_one(
        {
            "$and": [
                {"lco_id": lco_id},
                FILTER_ARCHIVED_FALSE_DICT,
            ]
        }
    )
    if find_one_result is None:
        return None
    return __read_lco_recursively(LearningContentObject(find_one_result),
                                  None) if recursive_read else LearningContentObject(find_one_result)


def read_learning_content_objects_by_object_id(
        object_id: str, recursive_read: bool = True
) -> List[LearningContentObject] | None:
    find_result = get_mongo_db_client()[LEARNING_CONTENT_OBJECTS_COLLECTION_NAME].find(
        {
            "$and": [
                {"object_id": object_id},
                FILTER_ARCHIVED_FALSE_DICT,
            ]
        }
    )
    return [__read_lco_recursively(LearningContentObject(lco_dict), None) if recursive_read
            else LearningContentObject(lco_dict) for lco_dict in find_result]


def read_learning_content_object_by_object_id(
        object_id: str, recursive_read: bool = True) -> LearningContentObject | None:
    lcos = read_learning_content_objects_by_object_id(object_id, False)
    if lcos is None or len(lcos) == 0:
        return None
    if len(lcos) > 1:
        logger.warning(f"LCO with object ID {object_id} could not unambiguously be determined!")
    return __read_lco_recursively(lcos[0], None) if recursive_read else lcos[0]


def update_learning_content_object_by_lco_id(
        lco_id: str, preliminary_lco: LearningContentObject, recursive_read: bool = True
) -> LearningContentObject:
    # TODO: Validation?

    find_one_result = get_mongo_db_client()[
        LEARNING_CONTENT_OBJECTS_COLLECTION_NAME
    ].find_one(
        {
            "$and": [
                {"lco_id": lco_id},
                FILTER_ARCHIVED_FALSE_DICT,
            ]
        }
    )
    if find_one_result is None:
        raise LcoNotExistsError()

    now = current_datetime()

    def operation(client, session):
        # TODO: Archive only referenced LCOs and delete the others
        __process_learning_content_object_recursively(
            lco=LearningContentObject(find_one_result),
            parent_lco=None,
            lco_preprocessing_function=lambda lco, parent_lco: LearningContentObject(client[
                LEARNING_CONTENT_OBJECTS_COLLECTION_NAME].find_one(
                {
                    "$and": [
                        {"_id": lco._id},
                        FILTER_ARCHIVED_FALSE_DICT,
                    ]
                }
            )),
            lco_processing_function=lambda lco, parent_lco: client[
                LEARNING_CONTENT_OBJECTS_COLLECTION_NAME
            ].update_one(
                {
                    "$and": [
                        {"lco_id": lco.lco_id},
                        FILTER_ARCHIVED_FALSE_DICT,
                    ]
                },
                {
                    "$set": {
                        "archived": True,
                        "updated": now,
                    }
                },
                session=session,
            ),
        )

        def prepare_insert_function(lco, parent_lco):
            if lco.lco_id is None or lco.lco_id != lco_id:
                lco.lco_id = str(uuid.uuid4())
            lco.updated = now
            lco.parent_lco_id = None if parent_lco is None else parent_lco.lco_id
            return lco

        def insert_function(lco, parent_lco):
            insert_one_result = client[LEARNING_CONTENT_OBJECTS_COLLECTION_NAME].insert_one(
                lco.to_dict(), session=session
            )
            inserted_lco = DotDict()
            inserted_lco._id = insert_one_result.inserted_id
            return inserted_lco

        parent_lco = None
        if "parent_lco_id" in find_one_result:
            find_parent_result = get_mongo_db_client()[
                LEARNING_CONTENT_OBJECTS_COLLECTION_NAME
            ].find_one(
                {
                    "$and": [
                        {"lco_id": find_one_result.get("parent_lco_id")},
                        FILTER_ARCHIVED_FALSE_DICT,
                    ]
                }
            )
            if find_parent_result is not None:
                parent_lco = LearningContentObject(find_parent_result)

        preliminary_lco.lco_id = lco_id
        return __process_learning_content_object_recursively(
            lco=preliminary_lco,
            parent_lco=parent_lco,
            lco_preprocessing_function=prepare_insert_function,
            lco_processing_function=insert_function,
        )

    execute_mongo_operation_in_transaction(operation)
    return read_learning_content_object_by_lco_id(lco_id, recursive_read)


def __read_lco_recursively(lco: LearningContentObject,
                           parent_lco: LearningContentObject | None) -> LearningContentObject:
    def load_lco_function(l, pl):
        return LearningContentObject(get_mongo_db_client()[LEARNING_CONTENT_OBJECTS_COLLECTION_NAME].find_one(
            {
                "$and": [
                    {"_id": l._id},
                    FILTER_ARCHIVED_FALSE_DICT,
                ]
            }
        ))

    return __process_learning_content_object_recursively(
        lco=lco,
        parent_lco=parent_lco,
        lco_preprocessing_function=load_lco_function,
        lco_processing_function=lambda l, pl: l,
    )


def __handle_attribute_for_learning_content_object_processing(
        lco_attribute: LearningContentObjectAttribute,
        parent_lco: LearningContentObject,
        lco_preprocessing_function,
        lco_processing_function,
) -> LearningContentObjectAttribute | None:
    if type(lco_attribute.value) is dict:
        lco_attribute.value = __process_learning_content_object_recursively(
            lco=lco_attribute.value,
            parent_lco=parent_lco,
            lco_preprocessing_function=lco_preprocessing_function,
            lco_processing_function=lco_processing_function,
        )
        return lco_attribute
    elif type(lco_attribute.value) is list:
        for i, attribute_element in enumerate(lco_attribute.value):
            lco_attribute.value[i] = __process_learning_content_object_recursively(
                lco=attribute_element,
                parent_lco=parent_lco,
                lco_preprocessing_function=lco_preprocessing_function,
                lco_processing_function=lco_processing_function,
            )
    return lco_attribute


def __process_learning_content_object_recursively(lco, parent_lco, lco_preprocessing_function, lco_processing_function):
    if lco is None:
        return None
    lco = lco_preprocessing_function(lco, parent_lco)

    if lco.attributes is not None and len(lco.attributes) != 0:
        for i, attribute in enumerate(lco.attributes):
            lco.attributes[i] = (
                __handle_attribute_for_learning_content_object_processing(
                    lco_attribute=attribute, parent_lco=lco, lco_preprocessing_function=lco_preprocessing_function,
                    lco_processing_function=lco_processing_function
                )
            )

    return lco_processing_function(lco, parent_lco)
