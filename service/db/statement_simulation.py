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
from datetime import datetime
from typing import List

from error.tutorial_module import SimulationNotExistsException
from model.core.student_module import StatementSimulation
from service.db import get_mongo_db_client, STATEMENT_SIMULATIONS_COLLECTION_NAME, read_collection_documents


def create_statement_simulation(statement_simulation: StatementSimulation) -> StatementSimulation:
    statement_simulation.simulation_id = str(uuid.uuid4())
    statement_simulation_dict = statement_simulation.to_dict()
    get_mongo_db_client()[STATEMENT_SIMULATIONS_COLLECTION_NAME].insert_one(statement_simulation_dict)
    return StatementSimulation(statement_simulation_dict)


def delete_statement_simulation_by_simulation_id(simulation_id: str) -> None:
    get_mongo_db_client()[STATEMENT_SIMULATIONS_COLLECTION_NAME].delete_one({"simulation_id": simulation_id})


def read_statement_simulations_by_time_of_invocation_before_date(
        date: datetime,
) -> List[StatementSimulation]:
    return read_collection_documents(
        collection_name=STATEMENT_SIMULATIONS_COLLECTION_NAME,
        mongo_filer={"time_of_invocation": {"$lte": date}},
        document_processing_function=lambda document: StatementSimulation(document)
    )


def read_statement_simulations_with_next_statement_by_time_of_invocation_before_date(
        date: datetime,
) -> List[StatementSimulation]:
    return read_collection_documents(
        collection_name=STATEMENT_SIMULATIONS_COLLECTION_NAME,
        mongo_filer={"time_of_invocation": {"$lte": date}},
        mongo_projection={"subsequent_statements": False},
        document_processing_function=lambda document: StatementSimulation(document)
    )


def update_statement_simulation(statement_simulation: StatementSimulation) -> StatementSimulation:
    client = get_mongo_db_client()
    find_one_result = client[STATEMENT_SIMULATIONS_COLLECTION_NAME].find_one(
        {"simulation_id": statement_simulation.simulation_id}
    )
    if find_one_result is None:
        raise SimulationNotExistsException()

    statement_simulation_dict = statement_simulation.to_dict()
    get_mongo_db_client()[STATEMENT_SIMULATIONS_COLLECTION_NAME].replace_one(
        {"simulation_id": statement_simulation.simulation_id},
        statement_simulation_dict,
        upsert=True
    )
    return StatementSimulation(statement_simulation_dict)
