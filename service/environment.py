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

import os
from typing import List


def cors_allowed_origins() -> List[str]:
    cors_allowed_origins_str = os.environ.get("CORS_ALLOWED_ORIGINS", None)
    return [] if cors_allowed_origins_str is None else cors_allowed_origins_str.split(",")


def debug() -> bool:
    return os.environ.get("DEBUG", "False").lower() in (
        "true",
        "t",
        "1",
    )


def disabled_assistance_type_keys() -> List[str]:
    if "DISABLED_ASSISTANCE_TYPES" in os.environ:
        return os.environ["DISABLED_ASSISTANCE_TYPES"].split(",")
    else:
        return []


def environment_file_path() -> str:
    return os.environ.get("ENVIRONMENT_FILE_PATH", "tab.env")


def host() -> str:
    return os.environ.get("HOST", "0.0.0.0")


def internationalization_files_path() -> str:
    return os.environ.get("INTERNATIONALIZATION_FILE_PATH", "locale/")


def jwt_secret_key() -> str:
    return os.environ.get("JWT_SECRET_KEY", "secret")


def mongo_database() -> str:
    return os.environ.get("MONGO_DATABASE", "tab_db")


def mongo_host() -> str:
    return os.environ.get("MONGO_HOST", "127.0.0.1")


def mongo_port() -> int:
    return int(os.environ.get("MONGO_PORT", 27017))


def mongo_replica_set() -> str:
    return os.environ.get("MONGO_REPLICA_SET", None)


def mongo_transactions_supported() -> bool:
    if mongo_replica_set() is None:
        return False
    return os.environ.get("MONGO_TRANSACTIONS_SUPPORTED", "True").lower() in (
        "true",
        "t",
        "1",
    )


def ollama_url() -> str:
    return os.environ.get("OLLAMA_URL", "https://ollama.com")


def port() -> int:
    return int(os.environ.get("PORT", 8000))
