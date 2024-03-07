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

from error.student_module import StudentModelNotExistsError
from model.core import ModelList
from model.core.student_module import StudentModel
from service.datetime import current_datetime
from service.db import (
    get_mongo_db_client,
    STUDENT_MODELS_COLLECTION_NAME,
    read_collection_documents, EXPERIENCES_COLLECTION_NAME,
)
from service.db.experience import create_experience_objects


def create_student_model(student_model: StudentModel, recursive_read: bool = True) -> StudentModel:
    student_model.updated = current_datetime()
    student_model.experiences = [] if student_model.experiences is None or len(student_model.experiences) == 0 else [
        {"_id": created_experience._id} for created_experience in
        create_experience_objects(student_model.experiences, student_model.user_id)]

    student_model_dict = student_model.to_dict()
    get_mongo_db_client()[STUDENT_MODELS_COLLECTION_NAME].insert_one(student_model_dict)

    return read_student_model_by_user_id(student_model.user_id, recursive_read)


def delete_student_model_by_user_id(user_id: str) -> None:
    if not __exist_student_model_by_user_id(user_id):
        raise StudentModelNotExistsError()
    student_model = read_student_model_by_user_id(user_id, False)
    if student_model.experiences is not None and len(student_model.experiences) != 0:
        get_mongo_db_client()[EXPERIENCES_COLLECTION_NAME].delete_many({
            "_id": {
                "$in": [experience_ref._id for experience_ref in student_model.experiences]
            }
        })
    get_mongo_db_client()[STUDENT_MODELS_COLLECTION_NAME].replace_one(
        {"user_id": user_id}, StudentModel.create_with_default_parameters(user_id=user_id).to_dict()
    )


def read_or_create_student_model_by_user_id(user_id: str, recursive_read: bool = True) -> StudentModel:
    if __exist_student_model_by_user_id(user_id):
        return read_student_model_by_user_id(user_id, recursive_read)
    else:
        return create_student_model(
            StudentModel.create_with_default_parameters(user_id=user_id), recursive_read
        )


def read_student_model_assistance_level_by_user_id(user_id: str) -> int:
    student_model = read_student_model_by_user_id(user_id, False)
    if student_model is None:
        raise StudentModelNotExistsError()
    return (
        None
        if "assistance_level" not in student_model
        else student_model.assistance_level
    )


def read_student_model_by_user_id(user_id: str, recursive_read: bool = True) -> StudentModel | None:
    find_one_result = get_mongo_db_client()[STUDENT_MODELS_COLLECTION_NAME].find_one(
        {"user_id": user_id}
    )
    if find_one_result is None:
        return None
    return __load_experiences(find_one_result) if recursive_read else StudentModel(find_one_result)


def read_student_models(page: int = None, objects_per_page: int = None) -> ModelList:
    student_models = read_collection_documents(
        STUDENT_MODELS_COLLECTION_NAME,
        mongo_filer=None,
        objects_per_page=objects_per_page,
        page=page,
        document_processing_function=lambda document: __load_experiences(document)
    )

    return ModelList(
        model_list=student_models,
        model_list_name="students",
        total_number_of_models=get_mongo_db_client()[
            STUDENT_MODELS_COLLECTION_NAME
        ].count_documents({}),
        provided_number_of_models=len(student_models),
        page_number=page,
    )


def read_student_models_by_user_ids_and_online_and_cooperativeness(
        user_ids: List[str], online: bool, cooperativeness: bool) -> List[StudentModel]:
    return [StudentModel(student_model_dict) for student_model_dict in
            get_mongo_db_client()[STUDENT_MODELS_COLLECTION_NAME].find({
                "$and": [
                    {"online": online},
                    {"cooperativeness": cooperativeness},
                    {"user_id": {"$in": user_ids}}
                ]
            })]


def update_student_model_cooperativeness_by_user_id(
        user_id: str, cooperativeness: bool
) -> None:
    if not __exist_student_model_by_user_id(user_id):
        raise StudentModelNotExistsError()
    get_mongo_db_client()[STUDENT_MODELS_COLLECTION_NAME].update_one(
        {"user_id": user_id}, {"$set": {"cooperativeness": cooperativeness, }}
    )


def update_student_model_online_by_user_id(
        user_id: str, online: bool
) -> None:
    if not __exist_student_model_by_user_id(user_id):
        raise StudentModelNotExistsError()
    get_mongo_db_client()[STUDENT_MODELS_COLLECTION_NAME].update_one(
        {"user_id": user_id}, {"$set": {"online": online, }}
    )


def update_student_model_assistance_level_by_user_id(
        user_id: str, assistance_level: int
) -> None:
    if not __exist_student_model_by_user_id(user_id):
        raise StudentModelNotExistsError()
    get_mongo_db_client()[STUDENT_MODELS_COLLECTION_NAME].update_one(
        {"user_id": user_id}, {"$set": {"assistance_level": assistance_level, }}
    )


# TODO: Check if the usage of this method is really always required
def __exist_student_model_by_user_id(user_id: str) -> bool:
    return (
            get_mongo_db_client()[STUDENT_MODELS_COLLECTION_NAME].find_one(
                {"user_id": user_id}, {"_id": 1}
            )
            is not None
    )


def __load_experiences(student_model: dict) -> StudentModel:
    if "experiences" not in student_model or (not student_model.get("experiences")):
        return StudentModel(student_model)
    student_model["experiences"] = get_mongo_db_client()[EXPERIENCES_COLLECTION_NAME].find({
        "_id": {"$in": list(map(lambda experience_ref: experience_ref.get("_id"), student_model.get("experiences")))}
    })
    return StudentModel(student_model)
