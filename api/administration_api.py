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
    status, HTTPException,
)
from fastapi.encoders import jsonable_encoder

from api.security_api import get_token_bearerAuth
from model.api.extra_models import TokenModel  # noqa: F401
from model.api.setting import Setting as SettingSchema
from model.core.administration import Setting
from service.administration import read_setting_by_key, update_setting_by_key

router = APIRouter()


@router.get(
    "/api/v1/administration/setting/{key}",
    responses={
        200: {"model": SettingSchema, "description": "Successfully retrieved setting"},
        400: {"description": "Bad request"},
        401: {"description": "Authentication failed"},
        404: {"description": "A setting with the specified key does not exist"},
    },
    tags=["Administration"],
    summary="Get setting",
    response_model_by_alias=True,
)
async def get_setting(
        key: str = Path(..., description="Unique key of a setting."),
        token_bearerAuth: TokenModel = Security(
            get_token_bearerAuth
        ),
) -> SettingSchema:
    """Get the setting with the specified key."""
    setting = read_setting_by_key(key)
    if setting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND
        )
    return SettingSchema.model_validate(setting.to_dict())


@router.put(
    "/api/v1/administration/setting/{key}",
    responses={
        204: {"description": "Successfully updated setting"},
        400: {"description": "Bad request"},
        401: {"description": "Authentication failed"},
        422: {"description": "Unprocessable entity"},
    },
    tags=["Administration"],
    summary="Update setting",
    response_model_by_alias=True,
)
async def update_setting(
        response: Response,
        key: str = Path(..., description="Unique key of a setting."),
        body: SettingSchema = Body(None, description=""),
        token_bearerAuth: TokenModel = Security(
            get_token_bearerAuth
        ),
) -> None:
    """Update the setting with the specified key."""
    update_setting_by_key(
        key, Setting(jsonable_encoder(body, by_alias=False))
    )
    response.status_code = status.HTTP_204_NO_CONTENT
