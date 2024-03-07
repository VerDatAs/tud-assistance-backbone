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
)
from fastapi.security import HTTPAuthorizationCredentials

from model.api.jwt_request import JwtRequest
from model.api.jwt_response import JwtResponse
from service.authentication import create_jwt, decode_header_credentials

router = APIRouter()


@router.post(
    "/api/v1/auth/login",
    responses={
        201: {"model": JwtResponse, "description": "Created"},
    },
    tags=["Development"],
    summary="Generate a JWT",
    response_model_by_alias=True,
)
async def generate_jwt(
        body: JwtRequest = Body(None, description=""),
) -> JwtResponse:
    """Generate a JWT with the provided username and the Role ADMIN for development purposes."""
    jwt = create_jwt(body.actor_account_name, "ADMIN")
    decode_header_credentials(HTTPAuthorizationCredentials(scheme="Bearer", credentials=jwt))
    return JwtResponse(token=jwt)
