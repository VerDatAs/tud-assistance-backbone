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

from error.expert_module import (
    LcoTypeAlreadyExistsError,
    LcoTypeNotExistsError,
    LcoModelInUseError,
)
from model.core import ModelList
from model.core.expert_module import LearningContentObjectModel
from service.datetime import current_datetime
from service.db import (
    get_mongo_db_client,
    read_collection_documents,
    LEARNING_CONTENT_OBJECT_MODELS_COLLECTION_NAME,
    LEARNING_CONTENT_OBJECTS_COLLECTION_NAME,
)


# TODO: Check efficiency of methods

def create_learning_content_object_model(
        lco_model: LearningContentObjectModel,
) -> LearningContentObjectModel:
    client = get_mongo_db_client()
    if __exist_learning_content_object_model_by_lco_type(lco_model.lco_type):
        raise LcoTypeAlreadyExistsError()
    lco_model.updated = current_datetime()
    insert_one_result = client[
        LEARNING_CONTENT_OBJECT_MODELS_COLLECTION_NAME
    ].insert_one(lco_model.to_dict())
    return LearningContentObjectModel(
        client[LEARNING_CONTENT_OBJECT_MODELS_COLLECTION_NAME].find_one(
            {"_id": insert_one_result.inserted_id}
        )
    )


def delete_learning_content_object_model_by_lco_type(lco_type: str) -> None:
    __validate_whether_lco_type_model_can_be_modified(lco_type)

    get_mongo_db_client()[LEARNING_CONTENT_OBJECT_MODELS_COLLECTION_NAME].delete_one(
        {"lco_type": lco_type}
    )


def read_learning_content_object_models(
        page: int = None, objects_per_page: int = None
) -> ModelList:
    lco_models = read_collection_documents(
        collection_name=LEARNING_CONTENT_OBJECT_MODELS_COLLECTION_NAME,
        objects_per_page=objects_per_page,
        page=page,
        document_processing_function=lambda document: LearningContentObjectModel(document)
    )

    return ModelList(
        model_list=lco_models,
        model_list_name="lco_models",
        total_number_of_models=get_mongo_db_client()[
            LEARNING_CONTENT_OBJECT_MODELS_COLLECTION_NAME
        ].count_documents({}),
        provided_number_of_models=len(lco_models),
        page_number=page,
    )


def read_learning_content_object_model_by_lco_type(
        lco_type: str,
) -> LearningContentObjectModel:
    find_one_result = get_mongo_db_client()[
        LEARNING_CONTENT_OBJECT_MODELS_COLLECTION_NAME
    ].find_one({"lco_type": lco_type})
    return (
        None if find_one_result is None else LearningContentObjectModel(find_one_result)
    )


def update_learning_content_object_model_by_lco_type(
        lco_type: str, lco_model: LearningContentObjectModel
) -> LearningContentObjectModel:
    __validate_whether_lco_type_model_can_be_modified(lco_type)

    client = get_mongo_db_client()

    lco_model.lco_type = lco_type
    lco_model.updated = current_datetime()
    replace_one_result = get_mongo_db_client()[
        LEARNING_CONTENT_OBJECT_MODELS_COLLECTION_NAME
    ].replace_one({"lco_type": lco_type}, lco_model.to_dict())

    return LearningContentObjectModel(
        client[LEARNING_CONTENT_OBJECT_MODELS_COLLECTION_NAME].find_one(
            {"_id": replace_one_result.raw_result.get("_id")}
        )
    )


def read_number_of_lcos_by_lco_type(lco_type: str) -> int:
    return get_mongo_db_client()[
        LEARNING_CONTENT_OBJECTS_COLLECTION_NAME
    ].count_documents({"lco_type": lco_type})


def __exist_learning_content_object_model_by_lco_type(lco_type: str) -> bool:
    return (
        False
        if get_mongo_db_client()[
               LEARNING_CONTENT_OBJECT_MODELS_COLLECTION_NAME
           ].find_one({"lco_type": lco_type}, {"_id": 1})
           is None
        else True
    )


def __validate_whether_lco_type_model_can_be_modified(lco_type) -> None:
    client = get_mongo_db_client()
    if (
            client[LEARNING_CONTENT_OBJECT_MODELS_COLLECTION_NAME].find_one(
                {"lco_type": lco_type}, {"_id": 1}
            )
            is None
    ):
        raise LcoTypeNotExistsError()
    if read_number_of_lcos_by_lco_type(lco_type) != 0:
        raise LcoModelInUseError()
