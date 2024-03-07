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

from typing import Dict, List  # noqa: F401

from fastapi import (  # noqa: F401
    APIRouter,
    Body,
    Cookie,
    Depends,
    Form,
    Header,
    Path,
    Query,
    Response,
    Security,
    status,
    HTTPException,
)
from fastapi.encoders import jsonable_encoder

from api.security_api import get_token_bearerAuth
from error.tutorial_module import (
    AssistanceNotExistsException,
    CompletedAssistanceModifyException,
)
from model.api.assistance import Assistance
from model.api.assistance_bundle import AssistanceBundle
from model.api.assistance_initiation_request import AssistanceInitiationRequest
from model.api.assistance_object_record_list import AssistanceObjectRecordList
from model.api.assistance_parameter_search_parameter import (
    AssistanceParameterSearchParameter,
)
from model.api.assistance_record import AssistanceRecord
from model.api.assistance_record_list import AssistanceRecordList
from model.api.assistance_response_object import AssistanceResponseObject
from model.api.extra_models import TokenModel  # noqa: F401
from model.api.get_assistance_process_type_key200_response import GetAssistanceProcessTypeKey200Response
from model.api.query_statements_request import QueryStatementsRequest
from model.api.query_statements_result import QueryStatementsResult
from model.api.simulation_id import SimulationId
from model.api.statement_processing_request import StatementProcessingRequest
from model.api.statement_simulation_request import StatementSimulationRequest
from model.core.student_module import Statement, StatementSimulation
from model.core.tutorial_module import (
    AssistanceParameter,
    AssistanceParameterSearchCriteria,
    AssistanceContext,
    AssistanceObject,
)
from model.service.assistance import (
    AssistanceRequest,
    ASSISTANCE_OPERATION_KEY_INITIATION,
)
from service.assistance import (
    get_assistance_initiation_parameters_dict,
    assistance_by_request,
    assistance_by_statement,
    update_assistance, assistance_by_simulation,
)
from service.backend import send_assistance
from service.db.assistance import (
    read_assistance_by_a_id,
    read_assistance,
    read_assistance_by_search_criteria,
)
from service.db.assistance_object import read_assistance_objects_by_search_criteria
from service.db.statement import get_attribute_suggestions, query_statements, read_statement_schema

router = APIRouter()


@router.get(
    "/api/v1/assistance/{aId}",
    responses={
        200: {
            "model": AssistanceRecord,
            "description": "Successfully retrieved assistance process",
        },
        401: {"description": "Authentication failed"},
        404: {
            "description": "An assistance process with the provided ID does not exist"
        },
    },
    tags=["Tutorial Module"],
    summary="Get assistance process",
    response_model_by_alias=True,
)
async def get_assistance_process(
        aId: str = Path(..., description="Unique ID of an assistance process."),
        token_bearerAuth: TokenModel = Security(get_token_bearerAuth),
) -> AssistanceRecord:
    """Get the assistance processes with the specified ID."""
    assistance = read_assistance_by_a_id(aId)
    if assistance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return AssistanceRecord.model_validate(assistance.to_dict())


@router.get(
    "/api/v1/assistance/{aId}/type",
    responses={
        200: {"model": GetAssistanceProcessTypeKey200Response,
              "description": "Successfully retrieved assistance process type key"},
        401: {"description": "Authentication failed"},
        404: {"description": "An assistance process with the provided ID does not exist"},
    },
    tags=["Tutorial Module"],
    summary="Get assistance process type key",
    response_model_by_alias=True,
)
async def get_assistance_process_type_key(
        aId: str = Path(..., description="Unique ID of an assistance process."),
        token_bearerAuth: TokenModel = Security(
            get_token_bearerAuth
        ),
) -> GetAssistanceProcessTypeKey200Response:
    """Get the type key of the assistance processes with the specified ID."""
    assistance = read_assistance_by_a_id(aId)
    if assistance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return GetAssistanceProcessTypeKey200Response(type_key=assistance.type_key)


@router.get(
    "/api/v1/assistance",
    responses={
        200: {
            "model": AssistanceRecordList,
            "description": "Successfully retrieved assistance processes",
        },
        400: {"description": "Bad request"},
        401: {"description": "Authentication failed"},
    },
    tags=["Tutorial Module"],
    summary="Get assistance processes",
    response_model_by_alias=True,
)
async def get_assistance_processes(
        page: int = Query(
            None,
            description="The page that should be delivered. The default value is one.",
            ge=1,
        ),
        objects_per_page: int = Query(
            None,
            description="The number of objects that should be delivered per page. If this is not specified, all objects are delivered. This has to be specified when a page number is specified.",
            ge=1,
        ),
        token_bearerAuth: TokenModel = Security(get_token_bearerAuth),
) -> AssistanceRecordList:
    """Get all assistance processes."""
    try:
        assistance = read_assistance(page, objects_per_page)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e) if str(e) else None,
        )

    return AssistanceRecordList.model_validate(assistance.to_dict())


@router.post(
    "/api/v1/assistance",
    responses={
        200: {
            "model": AssistanceBundle,
            "description": "Successfully initiated assistance",
        },
        204: {
            "description": "Successfully initiated assistance, assistance is provided asynchronously"
        },
        400: {"description": "Bad Request"},
        401: {"description": "Authentication failed"},
        404: {"description": "Assistance type not found"},
        422: {"description": "Unprocessable entity"},
    },
    tags=["Tutorial Module"],
    summary="Initiate assistance process",
    response_model_by_alias=True,
)
async def initiate_assistance_process(
        response: Response,
        body: AssistanceInitiationRequest = Body(None, description=""),
        token_bearerAuth: TokenModel = Security(get_token_bearerAuth),
) -> AssistanceBundle | None:
    """Initiate an assistance process that has to be triggered proactively."""
    try:
        assistance = assistance_by_request(
            AssistanceRequest(
                assistance_type_key=body.type,
                assistance_operation_key=ASSISTANCE_OPERATION_KEY_INITIATION,
                ctx=AssistanceContext(
                    get_assistance_initiation_parameters_dict(
                        list(
                            map(
                                lambda parameter: AssistanceParameter(
                                    jsonable_encoder(parameter)
                                ),
                                body.parameters,
                            )
                        )
                    )
                ),
            )
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e) if str(e) else None,
        )

    if assistance is not None and assistance.assistance is not None:
        send_assistance(assistance.assistance)
    return AssistanceBundle(
        assistance=list(map(lambda a: Assistance.model_validate(a.to_dict()), assistance.assistance)))


@router.post(
    "/api/v1/statement",
    responses={
        200: {
            "model": AssistanceBundle,
            "description": "Successfully processed statement",
        },
        204: {
            "description": "Successfully processed statement, assistance is provided asynchronously"
        },
        400: {"description": "Bad request"},
        401: {"description": "Authentication failed"},
        404: {
            "description": "Corresponding student or referenced learning content elements not found"
        },
        422: {"description": "Unprocessable entity"},
    },
    tags=["Tutorial Module"],
    summary="Process xAPI statement",
    response_model_by_alias=True,
)
async def process_xapi_statement(
        response: Response,
        body: StatementProcessingRequest = Body(None, description=""),
        token_bearerAuth: TokenModel = Security(get_token_bearerAuth),
) -> AssistanceBundle | None:
    """Process an xAPI statement, taking the previously received statements into account. When appropriate, assistance corresponding the learning process is initiated."""
    assistance = assistance_by_statement(
        Statement(jsonable_encoder(body.statement)),
        list(
            map(
                lambda supported_assistance_type: supported_assistance_type.key,
                body.supported_assistance_types,
            )
        ),
    )
    if assistance is not None and assistance.assistance is not None:
        send_assistance(assistance.assistance)
    response.status_code = status.HTTP_204_NO_CONTENT
    return None


@router.get(
    "/api/v1/statement/schema",
    responses={
        200: {"model": List[object], "description": "Successfully retrieved xAPI statement schema"},
        400: {"description": "Bad request"},
        401: {"description": "Authentication failed"},
    },
    tags=["Tutorial Module"],
    summary="Get xAPI statements schema",
    response_model_by_alias=True,
)
async def get_xapi_statement_schema(
        token_bearerAuth: TokenModel = Security(get_token_bearerAuth),
) -> List[object]:
    """Get the schema of the xAPI statements."""
    try:
        result = read_statement_schema()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e) if str(e) else None,
        )

    return result


@router.get(
    "/api/v1/statement/{attribute}/suggestions",
    responses={
        200: {"model": List[str], "description": "Successfully retrieved suggestions for xAPI statement attributes"},
        400: {"description": "Bad request"},
        401: {"description": "Authentication failed"},
    },
    tags=["Tutorial Module"],
    summary="Get suggestions for xAPI statement attributes",
    response_model_by_alias=True,
)
async def get_xapi_statement_suggestions(
        attribute: str = Path(..., description="Name of the xAPI statement attribute."),
        suggest: str = Query(None, description="The current input for the attribute.", alias="suggest"),
        token_bearerAuth: TokenModel = Security(get_token_bearerAuth),
) -> List[str]:
    """Get suggestions for xAPI statement attributes."""
    try:
        result = get_attribute_suggestions(attribute, suggest)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e) if str(e) else None,
        )

    return result


@router.post(
    "/api/v1/statement/query",
    responses={
        200: {"model": QueryStatementsResult, "description": "Successfully queried and aggregated statements"},
        400: {"description": "Bad request"},
        401: {"description": "Authentication failed"},
    },
    tags=["Tutorial Module"],
    summary="Query xAPI statements",
    response_model_by_alias=True,
)
async def query_xapi_statements(
        body: QueryStatementsRequest = Body(None, description=""),
        token_bearerAuth: TokenModel = Security(get_token_bearerAuth),
) -> QueryStatementsResult:
    """Query xAPI statements based on filter and aggregation operations."""
    try:
        query_result = query_statements(body)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e) if str(e) else None,
        )

    return QueryStatementsResult.model_validate(query_result.to_dict())


@router.post(
    "/api/v1/simulation",
    responses={
        200: {"model": SimulationId, "description": "Successfully initiated statement simulation"},
        400: {"description": "Bad request"},
        401: {"description": "Authentication failed"},
        422: {"description": "Unprocessable entity"},
    },
    tags=["Tutorial Module"],
    summary="Simulate xAPI statement execution",
    response_model_by_alias=True,
)
async def simulate_xapi_statement_execution(
        body: StatementSimulationRequest = Body(None, description=""),
        token_bearerAuth: TokenModel = Security(
            get_token_bearerAuth
        ),
) -> SimulationId:
    """Simulate the execution of a number xAPI statements."""
    if not body.statements or len(body.statements) < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str("At least one statement has to be provided for the simulation!"),
        )
    statement_simulation = assistance_by_simulation(StatementSimulation.create_with_default_parameters(
        next_statement=Statement(jsonable_encoder(body.statements[0])),
        subsequent_statements=[Statement(jsonable_encoder(statement)) for statement in body.statements[1:]],
        supported_assistance_types=[supported_assistance_type.key for supported_assistance_type in
                                    body.supported_assistance_types],
        time_factor=body.time_factor if body.time_factor is not None else 1.0,
        user_id=body.user_id))
    return SimulationId(simulation_id=statement_simulation.simulation_id)


@router.post(
    "/api/v1/assistance-object/search",
    responses={
        200: {
            "model": AssistanceRecordList,
            "description": "Successfully retrieved assistance objects",
        },
        204: {"description": "No assistance object fulfills the search query"},
        400: {"description": "Bad request"},
        401: {"description": "Authentication failed"},
        422: {"description": "Unprocessable entity"},
    },
    tags=["Tutorial Module"],
    summary="Search for assistance objects",
    response_model_by_alias=True,
)
async def search_for_assistance_objects(
        body: List[AssistanceParameterSearchParameter] = Body(None, description=""),
        page: int = Query(
            None,
            description="The page that should be delivered. The default value is one.",
            ge=1,
        ),
        objects_per_page: int = Query(
            None,
            description="The number of objects that should be delivered per page. If this is not specified, all objects are delivered. This has to be specified when a page number is specified.",
            ge=1,
        ),
        token_bearerAuth: TokenModel = Security(get_token_bearerAuth),
) -> AssistanceObjectRecordList | None:
    """Search for assistance objects by parameters."""
    try:
        assistance_object_list = read_assistance_objects_by_search_criteria(
            list(
                map(
                    lambda attribute_search_parameter: AssistanceParameterSearchCriteria(
                        jsonable_encoder(attribute_search_parameter)
                    ),
                    body,
                )
            ),
            page,
            objects_per_page,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e) if str(e) else None,
        )

    return AssistanceObjectRecordList.model_validate(assistance_object_list.to_dict())


@router.post(
    "/api/v1/assistance/search",
    responses={
        200: {
            "model": AssistanceRecordList,
            "description": "Successfully retrieved assistance processes",
        },
        400: {"description": "Bad request"},
        401: {"description": "Authentication failed"},
        422: {"description": "Unprocessable entity"},
    },
    tags=["Tutorial Module"],
    summary="Search for assistance processes",
    response_model_by_alias=True,
)
async def search_for_assistance_processes(
        body: List[AssistanceParameterSearchParameter] = Body(None, description=""),
        page: int = Query(
            None,
            description="The page that should be delivered. The default value is one.",
            ge=1,
        ),
        objects_per_page: int = Query(
            None,
            description="The number of objects that should be delivered per page. If this is not specified, all objects are delivered. This has to be specified when a page number is specified.",
            ge=1,
        ),
        token_bearerAuth: TokenModel = Security(get_token_bearerAuth),
) -> AssistanceRecordList | None:
    """Search for assistance processes by parameters."""
    try:
        assistance_list = read_assistance_by_search_criteria(
            list(
                map(
                    lambda attribute_search_parameter: AssistanceParameterSearchCriteria(
                        jsonable_encoder(attribute_search_parameter)
                    ),
                    body,
                )
            ),
            page,
            objects_per_page,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e) if str(e) else None,
        )

    return AssistanceRecordList.model_validate(assistance_list.to_dict())


@router.post(
    "/api/v1/assistance/{aId}",
    responses={
        200: {
            "model": AssistanceBundle,
            "description": "Successfully updated assistance process",
        },
        204: {
            "description": "Successfully updated assistance process, assistance is provided asynchronously"
        },
        400: {"description": "Bad request"},
        401: {"description": "Authentication failed"},
        422: {"description": "Unprocessable entity"},
    },
    tags=["Tutorial Module"],
    summary="Update assistance process",
    response_model_by_alias=True,
)
async def update_assistance_process(
        response: Response,
        aId: str = Path(..., description="Unique ID of an assistance process."),
        body: List[AssistanceResponseObject] = Body(None, description=""),
        token_bearerAuth: TokenModel = Security(get_token_bearerAuth),
) -> AssistanceBundle | None:
    """Post an Assistance Object which data are used to update the state of the corresponding assistance process."""
    try:
        assistance = update_assistance(
            aId,
            list(
                map(
                    lambda assistance_response_object: AssistanceObject(
                        jsonable_encoder(assistance_response_object, by_alias=False)
                    ),
                    body,
                )
            ),
        )
    except (AssistanceNotExistsException, CompletedAssistanceModifyException):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    if assistance is not None and assistance.assistance is not None:
        send_assistance(assistance.assistance)
    response.status_code = status.HTTP_204_NO_CONTENT
    return None
