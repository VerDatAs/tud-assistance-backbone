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

from datetime import timedelta, datetime
from typing import List

from loguru import logger

from model.core.tutorial_module import (
    AssistanceOperation,
)
from service.datetime import current_datetime, datetime_to_string
from service.db import (
    get_mongo_db_client,
    ASSISTANCE_OPERATIONS_COLLECTION_NAME,
    read_collection_documents,
)


def create_assistance_operation_for_scheduled_invocation(
        assistance_operation: AssistanceOperation, time_to_invocation_in_s: float
) -> AssistanceOperation:
    assistance_operation.time_of_invocation = current_datetime() + timedelta(
        seconds=time_to_invocation_in_s
    )

    logger.info(
        f"Schedule operation {assistance_operation.assistance_operation_key} for {assistance_operation.assistance_type_key} for {assistance_operation.a_id} for {datetime_to_string(assistance_operation.time_of_invocation)}")

    assistance_operation_dict = assistance_operation.to_dict()
    get_mongo_db_client()[ASSISTANCE_OPERATIONS_COLLECTION_NAME].insert_one(
        assistance_operation_dict
    )

    return AssistanceOperation(assistance_operation_dict)


def delete_assistance_operation(assistance_operation: AssistanceOperation) -> None:
    get_mongo_db_client()[ASSISTANCE_OPERATIONS_COLLECTION_NAME].delete_one({"_id": assistance_operation._id})


def delete_assistance_operations_by_a_id(a_id: str) -> None:
    get_mongo_db_client()[ASSISTANCE_OPERATIONS_COLLECTION_NAME].delete_many({"a_id": a_id})


def read_assistance_operations() -> List[AssistanceOperation]:
    return read_collection_documents(
        collection_name=ASSISTANCE_OPERATIONS_COLLECTION_NAME,
        document_processing_function=lambda document: AssistanceOperation(document)
    )


def read_assistance_operation_by_time_of_invocation_before_date(
        date: datetime,
) -> List[AssistanceOperation]:
    return read_collection_documents(
        collection_name=ASSISTANCE_OPERATIONS_COLLECTION_NAME,
        mongo_filer={"time_of_invocation": {"$lte": date}},
        document_processing_function=lambda document: AssistanceOperation(document)
    )
