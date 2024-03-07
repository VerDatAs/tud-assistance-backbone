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
from model.api.assistance_language_list import AssistanceLanguageList
from model.api.assistance_type import AssistanceType
from model.api.assistance_type_list import AssistanceTypeList
from model.api.extra_models import TokenModel  # noqa: F401
from model.core.tutorial_module import KindOfAssistanceType
from service.assistance import (
    get_assistance_type as get_assistance_type_definition,
    get_assistance_types,
)
from service.i18n import get_supported_locales

router = APIRouter()


@router.get(
    "/api/v1/assistance-type/{key}",
    responses={
        200: {
            "model": AssistanceType,
            "description": "Successfully retrieved assistance type",
        },
        400: {"description": "Bad request"},
        401: {"description": "Authentication failed"},
        404: {
            "description": "An assistance type with the specified key does not exist"
        },
    },
    tags=["Provisioning"],
    summary="Get assistance type",
    response_model_by_alias=True,
)
async def get_assistance_type(
        key: str = Path(..., description="Unique key of an assistance type."),
        token_bearerAuth: TokenModel = Security(get_token_bearerAuth),
) -> AssistanceType:
    """Get the assistance type with the specified key."""
    assistance_type = get_assistance_type_definition(key)
    if assistance_type is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return AssistanceType.model_validate(assistance_type.to_dict())


@router.get(
    "/api/v1/assistance-language",
    responses={
        200: {
            "model": AssistanceLanguageList,
            "description": "Successfully retrieved supported assistance languages",
        },
        400: {"description": "Bad request"},
        401: {"description": "Authentication failed"},
    },
    tags=["Provisioning"],
    summary="Get supported assistance languages",
    response_model_by_alias=True,
)
async def get_supported_assistance_languages(
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
) -> AssistanceLanguageList:
    """Get the assistance languages that are supported by the system."""
    supported_assistance_languages = get_supported_locales()

    if page is None and objects_per_page is None:
        assistance_languages = supported_assistance_languages
        page_number = 1
    elif page is not None and objects_per_page is not None:
        assistance_languages = supported_assistance_languages[
                               ((page - 1) * objects_per_page): (page * objects_per_page)
                               ]
        page_number = page
    elif page is None and objects_per_page is not None:
        assistance_languages = supported_assistance_languages[:objects_per_page]
        page_number = 1
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    return AssistanceLanguageList(
        languages=assistance_languages,
        total_number=len(supported_assistance_languages),
        provided_number=len(assistance_languages),
        page_number=page_number,
    )


@router.get(
    "/api/v1/assistance-type",
    responses={
        200: {
            "model": AssistanceTypeList,
            "description": "Successfully retrieved supported assistance types",
        },
        400: {"description": "Bad request"},
        401: {"description": "Authentication failed"},
    },
    tags=["Provisioning"],
    summary="Get supported assistance types",
    response_model_by_alias=True,
)
async def get_supported_assistance_types(
        kind: str = Query(
            None,
            description="The kind of assistance type that defines how data is provided to initiate the assistance and which information is provided during the assistance provision.",
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
) -> AssistanceTypeList:
    """Get the assistance types that are supported by the system."""
    supported_assistance_types = get_assistance_types(
        kind if kind is None else KindOfAssistanceType(kind)
    )

    if not supported_assistance_types:
        return AssistanceTypeList(
            types=[],
            total_number=0,
            provided_number=0,
            page_number=1 if page is None else page,
        )

    if page is None and objects_per_page is None:
        assistance_types = supported_assistance_types
        page_number = 1
    elif page is not None and objects_per_page is not None:
        assistance_types = supported_assistance_types[
                           ((page - 1) * objects_per_page): (page * objects_per_page)
                           ]
        page_number = page
    elif page is None and objects_per_page is not None:
        assistance_types = supported_assistance_types[:objects_per_page]
        page_number = 1
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    return AssistanceTypeList(
        types=list(
            map(lambda assistance_type: assistance_type.to_dict(), assistance_types)
        ),
        total_number=len(supported_assistance_types),
        provided_number=len(assistance_types),
        page_number=page_number,
    )
