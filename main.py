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

import logging
import sys
from datetime import timedelta

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_utilities import repeat_every
from loguru import logger
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match

from api.administration_api import router as administration_api_router
from api.development_api import router as development_api_router
from api.expert_module_api import router as expert_module_api_router
from api.provisioning_api import router as provisioning_api_router
from api.student_module_api import router as student_module_api_router
from api.tutorial_module_api import router as tutorial_module_api_router
from api.websocket_api import router as websocket_api_router
from service import full_stack
from service.administration import debug
from service.assistance import check_scheduled_assistance_operations, check_statements_to_simulate
from service.datetime import current_datetime
from service.db import disconnect_mongo_client
from service.db.assistance_operation import read_assistance_operation_by_time_of_invocation_before_date, \
    delete_assistance_operation
from service.environment import cors_allowed_origins, environment_file_path, host, port

load_dotenv(environment_file_path())

logger.remove()
logger.add(sys.stdout, colorize=True,
           format="<green>{time}</green> | {level:.1} | <level>{message}</level>")
logger.add("./log/tab.log", format="<green>{time}</green> | {level:.1} | <level>{message}</level>")

app = FastAPI(
    title="TUD Assistance Backbone API",
    description="System for providing information about a user as well as generating assistance or suggestions for a user with regard to received learning process data (i.e., xAPI statements).",
    version="1.0.0",
)


@app.on_event("startup")
async def startup_event():
    uvicorn_error = logging.getLogger("uvicorn.error")
    uvicorn_error.disabled = False
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.disabled = True
    logger.info("Started application")


@app.on_event("startup")
@repeat_every(seconds=2, raise_exceptions=True)
async def scheduled_check_for_assistance_operations_to_execute():
    try:
        check_scheduled_assistance_operations()
    except Exception:
        logger.error(f"An error occurred during the check for scheduled assistance operations! {full_stack()}")


@app.on_event("startup")
@repeat_every(seconds=2, raise_exceptions=True)
async def scheduled_check_for_statements_to_simulate():
    try:
        check_statements_to_simulate()
    except Exception:
        logger.error(f"An error occurred during the check for statements to simulate! {full_stack()}")


@app.on_event("startup")
@repeat_every(seconds=600, raise_exceptions=True)
async def scheduled_cleanup_for_expired_assistance_operations():
    assistance_operations = read_assistance_operation_by_time_of_invocation_before_date(
        current_datetime() - timedelta(hours=1))
    for assistance_operation in assistance_operations:
        try:
            delete_assistance_operation(assistance_operation)
        except Exception as e:
            logger.error(
                f"An error occurred during the deletion of operation {assistance_operation.assistance_operation_key} for {assistance_operation.a_id}! {full_stack()}")


@app.on_event("shutdown")
async def shutdown_event():
    disconnect_mongo_client()


app.include_router(administration_api_router)
if debug():
    app.include_router(development_api_router)
app.include_router(expert_module_api_router)
app.include_router(provisioning_api_router)
app.include_router(student_module_api_router)
app.include_router(tutorial_module_api_router)
app.include_router(websocket_api_router)


@app.middleware("http")
async def log_middle(request: Request, call_next):
    logger.info(f"{request.method} {request.url}")
    routes = request.app.router.routes
    logger.debug("Params:")
    for route in routes:
        match, scope = route.matches(request)
        if match == Match.FULL:
            for name, value in scope["path_params"].items():
                logger.debug(f"\t{name}: {value}")
    logger.debug("Headers:")
    for name, value in request.headers.items():
        logger.debug(f"\t{name}: {value}")

    try:
        if "content-length" in request.headers.keys():
            await request.body()
            body = await request.json()
            if body is not None:
                logger.debug("Body:")
                logger.debug(f"\t{body}")
    except Exception as e:
        logger.warning(f"An error occurred while logging the request body: {full_stack()}")

    try:
        return await call_next(request)
    except Exception as e:
        logger.error(f"An exception occurred during a request! {full_stack()}")
        return Response("Internal server error" + e.message if hasattr(e, "message") else "!", status_code=500)


app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == '__main__':
    uvicorn.run(app, host=host(), port=port())
