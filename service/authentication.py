"""
    Assistance Backbone for the assistance system developed as part of the VerDatAs project
    Copyright (C) 2022-2024 TU Dresden (Maximilian Brandt, Sebastian Kucharski)

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

from datetime import timedelta
from http.client import HTTPException

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from jwt import ExpiredSignatureError, InvalidSignatureError

from service.datetime import current_timestamp, current_datetime
from service.environment import jwt_secret_key

bearer_auth = HTTPBearer()

JWT_TOKEN_KEY_EXP = "exp"
JWT_TOKEN_KEY_IAT = "iat"
JWT_TOKEN_KEY_ISS = "iss"
JWT_TOKEN_KEY_ROLES = "roles"
JWT_TOKEN_KEY_SUB = "sub"


def create_jwt(username: str, role) -> str:
    return jwt.encode(
        {
            JWT_TOKEN_KEY_ISS: "self",
            JWT_TOKEN_KEY_SUB: username,
            JWT_TOKEN_KEY_IAT: int(current_timestamp()),
            JWT_TOKEN_KEY_EXP: int(
                (
                        current_datetime() + timedelta(hours=1)
                ).timestamp()
            ),
            JWT_TOKEN_KEY_ROLES: [role],
        },
        jwt_secret_key(),
        algorithm="HS256",
    )


def decode_jwt(token: str) -> str:
    return jwt.decode(token, jwt_secret_key(), algorithms=["HS256"])[JWT_TOKEN_KEY_SUB]


def decode_header_credentials(credentials: HTTPAuthorizationCredentials = Depends(bearer_auth)) -> str:
    try:
        return decode_jwt(credentials.credentials)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Expired token"
        )
    except InvalidSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
