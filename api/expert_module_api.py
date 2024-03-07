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
from fastapi.encoders import jsonable_encoder

from api.security_api import get_token_bearerAuth
from error.expert_module import (
    LcoTypeAlreadyExistsError,
    LcoInvalidError,
    LcoNotExistsError,
    LcoTypeNotExistsError,
    LcoModelInUseError, LcoWithObjectIdAlreadyExists,
)
from model.api.extra_models import TokenModel  # noqa: F401
from model.api.learning_content_object import (
    LearningContentObject as LearningContentObjectSchema,
)
from model.api.learning_content_object_attribute_search_parameter import (
    LearningContentObjectAttributeSearchParameter,
)
from model.api.learning_content_object_list import LearningContentObjectList
from model.api.learning_content_object_model import (
    LearningContentObjectModel as LearningContentObjectModelSchema,
)
from model.api.learning_content_object_model_list import (
    LearningContentObjectModelList as LearningContentObjectModelListSchema,
)
from model.api.learning_content_object_patch import LearningContentObjectPatch
from model.api.preliminary_learning_content_object import (
    PreliminaryLearningContentObject,
)
from model.core.expert_module import (
    LearningContentObject,
    LearningContentObjectModel,
    LearningContentObjectParameterSearchCriteria,
)
from service.db.learning_content_object import (
    create_learning_content_object as create_learning_content_object_in_db,
    delete_learning_content_object_by_lco_id,
    patch_learning_content_object as patch_learning_content_object_in_db,
    read_learning_content_object_by_lco_id,
    read_learning_content_objects,
    update_learning_content_object_by_lco_id,
    read_learning_content_objects_by_search_criteria,
)
from service.db.learning_content_object_model import (
    create_learning_content_object_model as create_learning_content_object_model_in_db,
    delete_learning_content_object_model_by_lco_type,
    read_learning_content_object_model_by_lco_type,
    read_learning_content_object_models,
    update_learning_content_object_model_by_lco_type,
)

router = APIRouter()


@router.post(
    "/api/v1/lco",
    responses={
        201: {
            "model": LearningContentObjectSchema,
            "description": "Successfully created Learning Content Object",
        },
        400: {"description": "Bad request"},
        401: {"description": "Authentication failed"},
        409: {"description": "LCO with object ID already exists"},
        422: {"description": "Unprocessable entity"},
    },
    tags=["Expert Module"],
    summary="Create Learning Content Object",
    response_model_by_alias=True,
)
async def create_learning_content_object(
        response: Response,
        body: PreliminaryLearningContentObject = Body(None, description=""),
        token_bearerAuth: TokenModel = Security(get_token_bearerAuth),
) -> LearningContentObjectSchema:
    """Create a Learning Content Object."""
    try:
        created_learning_content_object = create_learning_content_object_in_db(
            LearningContentObject(jsonable_encoder(body, by_alias=False))
        )
    except LcoInvalidError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e) if str(e) else None,
        )
    except LcoWithObjectIdAlreadyExists as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e) if str(e) else None,
        )
    created_learning_content_object = LearningContentObjectSchema.model_validate(
        created_learning_content_object.to_dict()
    )
    response.status_code = status.HTTP_201_CREATED
    return created_learning_content_object


@router.post(
    "/api/v1/lco-model",
    responses={
        201: {
            "model": LearningContentObjectModelSchema,
            "description": "Successfully created Learning Content Object Model",
        },
        400: {"description": "Bad request"},
        401: {"description": "Authentication failed"},
        409: {
            "description": "A Learning Content Object Model of the specified type does already exist"
        },
        422: {"description": "Unprocessable entity"},
    },
    tags=["Expert Module"],
    summary="Create Learning Content Object Model",
    response_model_by_alias=True,
)
async def create_learning_content_object_model(
        response: Response,
        body: LearningContentObjectModelSchema = Body(None, description=""),
        token_bearerAuth: TokenModel = Security(get_token_bearerAuth),
) -> LearningContentObjectModelSchema:
    """Create a metamodel that describes a Learning Content Object type."""
    try:
        created_learning_content_object_model = (
            create_learning_content_object_model_in_db(
                LearningContentObjectModel(jsonable_encoder(body, by_alias=False))
            )
        )
    except LcoTypeAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e) if str(e) else None,
        )
    created_learning_content_object_model = (
        LearningContentObjectModelSchema.model_validate(
            created_learning_content_object_model.to_dict()
        )
    )
    response.status_code = status.HTTP_201_CREATED
    return created_learning_content_object_model


@router.delete(
    "/api/v1/lco/{lcoId}",
    responses={
        204: {"description": "Successfully deleted Learning Content Object"},
        401: {"description": "Authentication failed"},
        404: {
            "description": "A Learning Content Object with the specified ID does not exist"
        },
    },
    tags=["Expert Module"],
    summary="Delete Learning Content Object",
    response_model_by_alias=True,
)
async def delete_learning_content_object(
        response: Response,
        lcoId: str = Path(..., description="Unique ID of a Learning Content Object."),
        token_bearerAuth: TokenModel = Security(get_token_bearerAuth),
) -> None:
    """Delete a Learning Content Object with the specified ID."""
    try:
        delete_learning_content_object_by_lco_id(lcoId)
    except LcoNotExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e) if str(e) else None,
        )
    response.status_code = status.HTTP_204_NO_CONTENT


@router.delete(
    "/api/v1/lco-model/{lcoType}",
    responses={
        200: {
            "model": LearningContentObjectModelSchema,
            "description": "Successfully deleted Learning Content Object Model",
        },
        401: {"description": "Authentication failed"},
        404: {
            "description": "A Learning Content Object Model for the specified type does not exist"
        },
        409: {
            "description": "Learning Content Objects of the type defined by the metamodel do exist"
        },
    },
    tags=["Expert Module"],
    summary="Delete Learning Content Object Model",
    response_model_by_alias=True,
)
async def delete_learning_content_object_model(
        response: Response,
        lcoType: str = Path(..., description="Unique identifier of an LCO-Model."),
        token_bearerAuth: TokenModel = Security(get_token_bearerAuth),
) -> None:
    """Delete a metamodel that describes a Learning Content Object type."""
    try:
        delete_learning_content_object_model_by_lco_type(lcoType)
    except LcoTypeNotExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e) if str(e) else None,
        )
    except LcoModelInUseError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e) if str(e) else None,
        )
    response.status_code = status.HTTP_204_NO_CONTENT


@router.get(
    "/api/v1/lco/{lcoId}",
    responses={
        200: {
            "model": LearningContentObjectSchema,
            "description": "Successfully retrieved Learning Content Object",
        },
        401: {"description": "Authentication failed"},
        404: {
            "description": "A Learning Content Object with the specified ID does not exist"
        },
    },
    tags=["Expert Module"],
    summary="Get Learning Content Object",
    response_model_by_alias=True,
)
async def get_learning_content_object(
        lcoId: str = Path(..., description="Unique ID of a Learning Content Object."),
        token_bearerAuth: TokenModel = Security(get_token_bearerAuth),
) -> LearningContentObjectSchema:
    """Get a Learning Content Object with the specified ID."""
    learning_content_object = read_learning_content_object_by_lco_id(lcoId)
    if learning_content_object is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return LearningContentObjectSchema.model_validate(learning_content_object.to_dict())


@router.get(
    "/api/v1/lco-model/{lcoType}",
    responses={
        200: {
            "model": LearningContentObjectModelSchema,
            "description": "Successfully retrieved Learning Content Object Model",
        },
        401: {"description": "Authentication failed"},
        404: {
            "description": "A Learning Content Object Model for the specified type does not exist"
        },
    },
    tags=["Expert Module"],
    summary="Get Learning Content Object Model",
    response_model_by_alias=True,
)
async def get_learning_content_object_model(
        lcoType: str = Path(..., description="Unique identifier of an LCO-Model."),
        token_bearerAuth: TokenModel = Security(get_token_bearerAuth),
) -> LearningContentObjectModelSchema:
    """Get a metamodel that describes a Learning Content Object type."""
    learning_content_object_model = read_learning_content_object_model_by_lco_type(
        lcoType
    )
    if learning_content_object_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return LearningContentObjectModelSchema.model_validate(
        learning_content_object_model.to_dict()
    )


@router.get(
    "/api/v1/lco-model",
    responses={
        200: {
            "model": LearningContentObjectModelListSchema,
            "description": "Successfully retrieved Learning Content Object Models",
        },
        400: {"description": "Bad request"},
        401: {"description": "Authentication failed"},
    },
    tags=["Expert Module"],
    summary="Get Learning Content Object Models",
    response_model_by_alias=True,
)
async def get_learning_content_object_models(
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
) -> LearningContentObjectModelListSchema | None:
    """Get all Learning Content Object Models."""
    try:
        learning_content_object_models = read_learning_content_object_models(
            page, objects_per_page
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e) if str(e) else None,
        )

    return LearningContentObjectModelListSchema.model_validate(
        learning_content_object_models.to_dict()
    )


@router.get(
    "/api/v1/lco",
    responses={
        200: {
            "model": LearningContentObjectList,
            "description": "Successfully retrieved Learning Content Objects",
        },
        400: {"description": "Bad request"},
        401: {"description": "Authentication failed"},
    },
    tags=["Expert Module"],
    summary="Get Learning Content Objects",
    response_model_by_alias=True,
)
async def get_learning_content_objects(
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
) -> LearningContentObjectList | None:
    """Get all Learning Content Objects."""
    try:
        learning_content_objects = read_learning_content_objects(page, objects_per_page)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e) if str(e) else None,
        )

    return LearningContentObjectList.model_validate(learning_content_objects.to_dict())


@router.patch(
    "/api/v1/lco/{lcoId}",
    responses={
        200: {
            "model": LearningContentObjectSchema,
            "description": "Successfully patched Learning Content Object",
        },
        400: {"description": "Bad request"},
        401: {"description": "Authentication failed"},
        404: {
            "description": "A Learning Content Object with the specified ID does not exist"
        },
        422: {"description": "Unprocessable entity"},
    },
    tags=["Expert Module"],
    summary="Patch Learning Content Object",
    response_model_by_alias=True,
)
async def patch_learning_content_object(
        lcoId: str = Path(..., description="Unique ID of a Learning Content Object."),
        body: List[LearningContentObjectPatch] = Body(None, description=""),
        token_bearerAuth: TokenModel = Security(get_token_bearerAuth),
) -> LearningContentObjectSchema:
    """Update certain parts of a Learning Content Object with the specified ID. The existing list of Learning Content Object attributes updated by applying the provided patches. If the list of attributes should be overwritten, the update operation has to be used. The patches are applied in the provided order."""
    try:
        patched_learning_content_object = patch_learning_content_object_in_db(
            lcoId,
            list(
                map(
                    lambda lco_patch: LearningContentObject(
                        jsonable_encoder(lco_patch, by_alias=False)
                    ),
                    body,
                )
            ),
        )
    except LcoNotExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e) if str(e) else None,
        )
    except LcoInvalidError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e) if str(e) else None,
        )
    return LearningContentObjectSchema.model_validate(
        patched_learning_content_object.to_dict()
    )


@router.post(
    "/api/v1/lco/search",
    responses={
        200: {
            "model": LearningContentObjectList,
            "description": "Successfully retrieved Learning Content Objects",
        },
        400: {"description": "Bad request"},
        401: {"description": "Authentication failed"},
        422: {"description": "Unprocessable entity"},
    },
    tags=["Expert Module"],
    summary="Search for Learning Content Objects",
    response_model_by_alias=True,
)
async def search_for_learning_content_objects(
        body: List[LearningContentObjectAttributeSearchParameter] = Body(
            None, description=""
        ),
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
) -> LearningContentObjectList | None:
    """Search for Learning Content Objects by attributes."""
    try:
        learning_content_objects = read_learning_content_objects_by_search_criteria(
            list(
                map(
                    lambda attribute_search_parameter: LearningContentObjectParameterSearchCriteria(
                        jsonable_encoder(attribute_search_parameter, by_alias=False)
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

    return LearningContentObjectList.model_validate(learning_content_objects.to_dict())


@router.put(
    "/api/v1/lco/{lcoId}",
    responses={
        200: {
            "model": LearningContentObjectSchema,
            "description": "Successfully updated Learning Content Object",
        },
        400: {"description": "Bad request"},
        401: {"description": "Authentication failed"},
        404: {
            "description": "A Learning Content Object with the specified ID does not exist"
        },
        422: {"description": "Unprocessable entity"},
    },
    tags=["Expert Module"],
    summary="Update Learning Content Object",
    response_model_by_alias=True,
)
async def update_learning_content_object(
        lcoId: str = Path(..., description="Unique ID of a Learning Content Object."),
        body: PreliminaryLearningContentObject = Body(None, description=""),
        token_bearerAuth: TokenModel = Security(get_token_bearerAuth),
) -> LearningContentObjectSchema:
    """Update a Learning Content Object with the specified ID."""
    try:
        updated_learning_content_object = update_learning_content_object_by_lco_id(
            lcoId, LearningContentObject(jsonable_encoder(body, by_alias=False))
        )
    except LcoNotExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e) if str(e) else None,
        )
    except LcoInvalidError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e) if str(e) else None,
        )
    return LearningContentObjectSchema.model_validate(
        updated_learning_content_object.to_dict()
    )


@router.put(
    "/api/v1/lco-model/{lcoType}",
    responses={
        200: {
            "model": LearningContentObjectModelSchema,
            "description": "Successfully updated Learning Content Object Model",
        },
        400: {"description": "Bad request"},
        401: {"description": "Authentication failed"},
        404: {
            "description": "A Learning Content Object Model for the specified type does not exist"
        },
        409: {
            "description": "Learning Content Objects of the type defined by the metamodel do exist"
        },
        422: {"description": "Unprocessable entity"},
    },
    tags=["Expert Module"],
    summary="Update Learning Content Object Model",
    response_model_by_alias=True,
)
async def update_learning_content_object_model(
        lcoType: str = Path(..., description="Unique identifier of an LCO-Model."),
        body: LearningContentObjectModelSchema = Body(None, description=""),
        token_bearerAuth: TokenModel = Security(get_token_bearerAuth),
) -> LearningContentObjectModelSchema:
    """Update a metamodel that describes a Learning Content Object type."""
    try:
        updated_learning_content_object_model = (
            update_learning_content_object_model_by_lco_type(
                lcoType, LearningContentObjectModel(jsonable_encoder(body, by_alias=False))
            )
        )
    except LcoTypeNotExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e) if str(e) else None,
        )
    except LcoModelInUseError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e) if str(e) else None,
        )
    return LearningContentObjectModelSchema.model_validate(
        updated_learning_content_object_model.to_dict()
    )
