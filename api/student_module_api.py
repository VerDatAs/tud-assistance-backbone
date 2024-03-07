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

from api.security_api import get_token_bearerAuth
from error.expert_module import LcoNotExistsError
from error.student_module import StudentModelNotExistsError
from model.api.extra_models import TokenModel  # noqa: F401
from model.api.get_assistance_level200_response import GetAssistanceLevel200Response
from model.api.set_assistance_level_request import SetAssistanceLevelRequest
from model.api.student_learning_content_object_progress import StudentLearningContentObjectProgress
from model.api.student_model import StudentModel
from model.api.student_model_list import StudentModelList
from model.api.student_progress_request import StudentProgressRequest
from service.db.student_model import (
    delete_student_model_by_user_id,
    read_student_model_by_user_id,
    read_student_models,
    read_student_model_assistance_level_by_user_id,
    update_student_model_assistance_level_by_user_id,
)
from service.student_model import get_student_lco_progress

router = APIRouter()


@router.get(
    "/api/v1/student/{userId}/assistance-level",
    responses={
        200: {
            "model": GetAssistanceLevel200Response,
            "description": "Successfully retrieved assistance level",
        },
        400: {"description": "Bad request"},
        401: {"description": "Authentication failed"},
        404: {"description": "User not found"},
    },
    tags=["Student Module"],
    summary="Get assistance level",
    response_model_by_alias=True,
)
async def get_assistance_level(
        userId: str = Path(..., description="Unique ID of a user."),
        token_bearerAuth: TokenModel = Security(get_token_bearerAuth),
) -> GetAssistanceLevel200Response:
    """Get the assistance level for a certain user with the specified ID."""
    try:
        assistance_level = read_student_model_assistance_level_by_user_id(userId)
    except StudentModelNotExistsError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return GetAssistanceLevel200Response(level=assistance_level)


@router.get(
    "/api/v1/student/{userId}",
    responses={
        200: {
            "model": StudentModel,
            "description": "Successfully retrieved student model",
        },
        400: {"description": "Bad request"},
        401: {"description": "Authentication failed"},
        404: {"description": "User not found"},
    },
    tags=["Student Module"],
    summary="Get student model",
    response_model_by_alias=True,
)
async def get_student_model(
        userId: str = Path(..., description="Unique ID of a user."),
        token_bearerAuth: TokenModel = Security(get_token_bearerAuth),
) -> StudentModel:
    """Get the student model for a certain user with the specified ID."""
    student_model = read_student_model_by_user_id(userId)
    if student_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return StudentModel.model_validate(student_model.to_dict())


@router.get(
    "/api/v1/student",
    responses={
        200: {
            "model": StudentModelList,
            "description": "Successfully retrieved Student Models",
        },
        400: {"description": "Bad request"},
        401: {"description": "Authentication failed"},
    },
    tags=["Student Module"],
    summary="Get Student Models",
    response_model_by_alias=True,
)
async def get_student_models(
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
) -> StudentModelList:
    """Get all Student Models."""
    try:
        student_models = read_student_models(page, objects_per_page)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e) if str(e) else None,
        )

    return StudentModelList.model_validate(student_models.to_dict())


@router.post(
    "/api/v1/student/progress",
    responses={
        200: {"model": StudentLearningContentObjectProgress, "description": "Successfully retrieved student progress"},
        400: {"description": "Bad request"},
        401: {"description": "Authentication failed"},
        404: {"description": "User not found"},
    },
    tags=["Student Module"],
    summary="Search for student progress",
    response_model_by_alias=True,
)
async def search_for_student_progress(
        student_progress_request: StudentProgressRequest = Body(None, description=""),
        token_bearerAuth: TokenModel = Security(
            get_token_bearerAuth
        ),
) -> StudentLearningContentObjectProgress:
    """Get the progress for a specific user with the specified ID for a specific LCO."""
    if student_progress_request is None or (
            student_progress_request.lco_id is None and student_progress_request.object_id is None):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    try:
        lco_progress = get_student_lco_progress(user_id=student_progress_request.user_id,
                                                lco_id=student_progress_request.lco_id,
                                                object_id=student_progress_request.object_id,
                                                include_sub_lcos=student_progress_request.sub_lcos)
    except (StudentModelNotExistsError, LcoNotExistsError) as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e) if str(e) else None,
        )
    except AttributeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    return StudentLearningContentObjectProgress.model_validate(lco_progress.to_dict())


@router.delete(
    "/api/v1/student/{userId}",
    responses={
        204: {"description": "Successfully reset student model"},
        400: {"description": "Bad request"},
        401: {"description": "Authentication failed"},
        404: {"description": "User not found"},
    },
    tags=["Student Module"],
    summary="Reset student model",
    response_model_by_alias=True,
)
async def reset_student_model(
        response: Response,
        userId: str = Path(..., description="Unique ID of a user."),
        token_bearerAuth: TokenModel = Security(get_token_bearerAuth),
) -> None:
    """Reset the student model for a certain user with the specified ID."""
    try:
        delete_student_model_by_user_id(userId)
    except StudentModelNotExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e) if str(e) else None,
        )
    response.status_code = status.HTTP_204_NO_CONTENT


@router.put(
    "/api/v1/student/{userId}/assistance-level",
    responses={
        200: {"description": "Successfully set assistance level"},
        400: {"description": "Bad request"},
        401: {"description": "Authentication failed"},
        404: {"description": "User not found"},
        422: {"description": "Unprocessable entity"},
    },
    tags=["Student Module"],
    summary="Set assistance level",
    response_model_by_alias=True,
)
async def set_assistance_level(
        userId: str = Path(..., description="Unique ID of a user."),
        set_assistance_level_request: SetAssistanceLevelRequest = Body(
            None, description=""
        ),
        token_bearerAuth: TokenModel = Security(get_token_bearerAuth),
) -> None:
    """Set the assistance level for a certain user."""
    try:
        update_student_model_assistance_level_by_user_id(
            userId, set_assistance_level_request.level
        )
    except StudentModelNotExistsError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
