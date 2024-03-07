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

from typing import List

import pymongo
from pymongo_schema.extract import extract_pymongo_client_schema

from model.api.query_statements_request import QueryStatementsRequest
from model.api.query_statements_result import QueryStatementsResult
from model.core import ModelList
from model.core.dot_dict import DotDict
from model.core.student_module import Statement
from service.db import get_mongo_db_client, STATEMENTS_COLLECTION_NAME
from service.environment import mongo_database, mongo_host, mongo_port, mongo_replica_set


def create_statement(statement: Statement) -> Statement:
    statement_dict = statement.to_dict()
    get_mongo_db_client()[STATEMENTS_COLLECTION_NAME].insert_one(statement_dict)
    return Statement(statement_dict)


def read_statement_by_id(statement_id: str) -> Statement:
    find_one_result = get_mongo_db_client()[STATEMENTS_COLLECTION_NAME].find_one({"id": statement_id})
    return None if find_one_result is None else Statement(find_one_result)


# Function to fetch suggestions for an xAPI Statement attribute based on the current user input
def get_attribute_suggestions(attribute: str, suggest: str) -> List[str]:
    client = get_mongo_db_client()
    # MongoDB function to get a list with all unique values for a field
    attribute_values = client[STATEMENTS_COLLECTION_NAME].distinct(attribute)

    suggestions = []

    # return the full list of suggestions if the user input is empty otherwise only values that (partly) match the current input
    if not suggest:
        suggestions = attribute_values
    else:
        suggestions = [k for k in attribute_values if suggest in k]

    return suggestions


# Function to extract the current schema of the xAPI Statements in the database
def read_statement_schema() -> List[object]:
    # external functionality that extracts the current schema
    with pymongo.MongoClient(host=mongo_host(), port=mongo_port(), replicaSet=mongo_replica_set()) as client:
        schema = extract_pymongo_client_schema(client, database_names=mongo_database(),
                                               collection_names=[STATEMENTS_COLLECTION_NAME])

    # return empty list if no schema could be extracted
    if len(schema) == 0:
        return []

    # access the object field since it contains the data we need
    attributes_statements = schema[mongo_database()][STATEMENTS_COLLECTION_NAME]['object']

    statement_schema = []
    # call another function to transform the data to the format that is required
    create_schema(attributes_statements, statement_schema)

    return statement_schema


# Recursive function to create a list which contains the attributes name and the corresponding type
def create_schema(attribute_object: object, result: list, parent_key: str = ""):
    for attribute in attribute_object:

        # Attributes that are currently not available to the user (could be extended/reduced in the future with feedback from the users)
        attributes_to_hide = ['_id', 'extensions', 'stored', 'version']
        if attribute in attributes_to_hide: continue

        # assemble the current attribute name/path
        current_key = attribute if parent_key == "" else parent_key + "." + attribute

        # recursively call this function again if the attribute is an object and contains further attributes
        # otherwise append attribute and type to the list
        if ('object' in attribute_object[attribute]):
            create_schema(attribute_object[attribute]['object'], result, current_key)
        else:
            result.append({
                "attribute": current_key,
                "type": attribute_object[attribute]['type']
            })


# Function that queries the database based on the user query
def query_statements(query: QueryStatementsRequest) -> QueryStatementsResult:
    client = get_mongo_db_client()

    aggregation_pipeline = []
    # add a new field to save the original timestamps in case the user wants to perform calculations with it in the query
    aggregation_pipeline.append({"$addFields": {"originalTimestamp": "$timestamp"}})

    # Transform the timestamp attribute to the ISO Date Standard and adjust to the format that is used for filtering
    aggregation_pipeline.append({"$addFields": {"timestamp": {"$toDate": "$timestamp"}}})
    aggregation_pipeline.append(
        {"$addFields": {"timestamp": {"$dateToString": {"date": "$timestamp", "format": "%Y-%m-%dT%H:%M"}}}})

    # assign the 'search' object of the query to the $match stage in the aggregation pipeline of MongoDB
    aggregation_pipeline.append({"$match": query.search})

    # Extend the pipeline with the list of operations the user specified in the query
    aggregation_pipeline.extend(query.operations)

    mongo_db_result = client[STATEMENTS_COLLECTION_NAME].aggregate(aggregation_pipeline)

    # Convert MongoDB result to a list
    result_as_list = list(map(lambda element: DotDict(element), mongo_db_result))

    result_list_name = 'statements'

    # if the result contains aggregation information, change the name for the ModelList since the structure is different to when filtered statements are the result
    if not (len(result_as_list) != 0 and result_as_list[0].has_key("actor")):
        result_list_name = 'aggregate'

    # return the result as a ModelList
    return ModelList(
        model_list=result_as_list,
        model_list_name=result_list_name,
        total_number_of_models=get_mongo_db_client()[
            STATEMENTS_COLLECTION_NAME
        ].count_documents({}),
        provided_number_of_models=len(result_as_list),
    )
