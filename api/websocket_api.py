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

import uuid

from fastapi import APIRouter, WebSocket
from loguru import logger

from service.stomp import stomp_server

router = APIRouter()


@router.websocket("/api/v1/websocket")
async def stomp_endpoint(ws: WebSocket):
    session_id = str(uuid.uuid4())
    await ws.accept()
    try:
        while True:
            data = await ws.receive_text()
            await stomp_server.process_stomp_message(data, ws, session_id)
    except Exception as e:
        if session_id in stomp_server.session_id_to_connections:
            logger.error(f"WebSocket Error! {e}")
    finally:
        await stomp_server.disconnect(session_id)
