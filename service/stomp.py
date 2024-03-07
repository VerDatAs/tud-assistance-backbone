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

import asyncio
import urllib.parse
import uuid
from datetime import timedelta
from typing import List, Any

import websocket
from fastapi import WebSocket
from jwt import ExpiredSignatureError
from loguru import logger

from service.authentication import decode_jwt
from service.datetime import current_datetime

STOMP_BYTE_NULL = "\x00"
STOMP_BYTE_LF = "\x0A"

STOMP_COMMAND_CONNECT = "CONNECT"
STOMP_COMMAND_CONNECTED = "CONNECTED"
STOMP_COMMAND_DISCONNECT = "DISCONNECT"
STOMP_COMMAND_ERROR = "ERROR"
STOMP_COMMAND_MESSAGE = "MESSAGE"
STOMP_COMMAND_SEND = "SEND"
STOMP_COMMAND_SUBSCRIBE = "SUBSCRIBE"
STOMP_COMMAND_UNSUBSCRIBE = "UNSUBSCRIBE"

STOMP_HEADER_KEY_ACCEPT_VERSION = "accept-version"
STOMP_HEADER_KEY_ACK = "ack"
STOMP_HEADER_KEY_CONTENT_TYPE = "content-type"
STOMP_HEADER_KEY_DESTINATION = "destination"
STOMP_HEADER_KEY_HEART_BEAT = "heart-beat"
STOMP_HEADER_KEY_HOST = "host"
STOMP_HEADER_KEY_ID = "id"
STOMP_HEADER_KEY_MESSAGE_ID = "message-id"
STOMP_HEADER_KEY_SESSION = "session"
STOMP_HEADER_KEY_SUBSCRIPTION = "subscription"
STOMP_HEADER_KEY_TOKEN = "token"
STOMP_HEADER_KEY_VERSION = "version"

STOMP_HEADER_VALUE_CONTENT_TYPE_JSON = "application/json"
STOMP_HEADER_VALUE_CONTENT_TYPE_TEXT = "text/plain"

STOMP_HEART_BEAT_PARAM_SX = 3
STOMP_HEART_BEAT_PARAM_SY = 3

STOMP_PROTOCOL_VERSION = "1.2"

STOMP_SUBSCRIPTION_DESTINATION_ASSISTANCE = "/assistance"
STOMP_SUBSCRIPTION_DESTINATION_STATEMENT = "/statement"

STOMP_SUBSCRIPTION_DESTINATIONS = [STOMP_SUBSCRIPTION_DESTINATION_ASSISTANCE, STOMP_SUBSCRIPTION_DESTINATION_STATEMENT]


class Frame:
    def __init__(self, command, headers, body):
        self.command = command
        self.headers = headers
        self.body = "" if body is None else body

    def __str__(self):
        lines = [self.command]
        skip_content_length = "content-length" in self.headers
        if skip_content_length:
            del self.headers["content-length"]

        for name in self.headers:
            value = self.headers[name]
            lines.append("" + name + ":" + value)

        if self.body is not None and not skip_content_length:
            lines.append(f"content-length:{self._calculate_content_length()}")

        lines.append(STOMP_BYTE_LF + self.body)
        return STOMP_BYTE_LF.join(lines)

    @staticmethod
    def unmarshall_single(data):
        lines = data.split(STOMP_BYTE_LF)

        command = lines[0].strip()
        headers = {}

        # get all headers
        i = 1
        while lines[i] != "":
            # get key, value from raw header
            (key, value) = lines[i].split(":")
            headers[key] = value
            i += 1

        # set body to None if there is no body
        body = None if lines[i + 1] == STOMP_BYTE_NULL else lines[i + 1][:-1]

        return Frame(command, headers, body)

    @staticmethod
    def marshall(command: str | None = None, headers: dict | None = None, body: Any | None = None) -> List[str]:
        if command is None and headers is None and body is None:
            frame = STOMP_BYTE_LF
        else:
            frame = str(Frame(command, headers, body)) + STOMP_BYTE_NULL
        return [frame[i:i + 8000] for i in range(0, len(frame), 8000)]

    def _calculate_content_length(self):
        escaped_str = urllib.parse.quote_plus(self.body)
        if "%" not in escaped_str:
            return len(self.body)
        count = len(escaped_str.split("%")) - 1
        if count == 0:
            count += 1
        tmp = len(escaped_str) - (count * 3)
        return count + tmp


class StompUtils:
    @staticmethod
    async def transmit(ws: WebSocket | websocket.WebSocketApp, command: str | None = None, headers: dict | None = None,
                       body: Any | None = None) -> None:
        out = Frame.marshall(command, headers, body)
        for o in out:
            logger.info(">>> " + o.replace("\n", " // "))
            await ws.send_text(o)


class StompSubscription:
    def __init__(self, session_id: str, subscription_id: str, destination: str):
        self.session_id = session_id
        self.subscription_id = subscription_id
        self.destination = destination


class StompServer:
    def __init__(self):
        self.heartbeat_interval = 3
        self.session_id_to_connections = {}
        self.session_id_to_last_transmission_date = {}
        self.session_id_to_subscriptions = {}

    async def _schedule_heart_beats(self, ws: WebSocket, session_id: str, interval_in_ms: int):
        try:
            while True:
                if session_id not in self.session_id_to_connections:
                    break
                await StompUtils.transmit(ws)
                await asyncio.sleep(interval_in_ms / 1000)
        except Exception as e:
            logger.error("Heart beat failed!", e)

    async def _schedule_heart_beat_checks(self, session_id: str, interval_in_ms: int):
        missing_heart_beats = 0
        try:
            while True:
                if session_id not in self.session_id_to_connections:
                    self.session_id_to_last_transmission_date.pop(session_id)
                    break
                if self.session_id_to_last_transmission_date[session_id] + timedelta(hours=1) < current_datetime():
                    missing_heart_beats += 1
                    if missing_heart_beats >= 3:
                        await self.disconnect(session_id)
                    continue
                missing_heart_beats = 0
                await asyncio.sleep(interval_in_ms / 1000)
        except Exception as e:
            logger.error("Heart beat check failed!", e)

    async def _send_error_and_close_connection(self, session_id: str, error_message: str) -> None:
        await StompUtils.transmit(
            self.session_id_to_connections[session_id],
            STOMP_COMMAND_ERROR,
            {STOMP_HEADER_KEY_VERSION: STOMP_PROTOCOL_VERSION,
             STOMP_HEADER_KEY_CONTENT_TYPE: STOMP_HEADER_VALUE_CONTENT_TYPE_TEXT},
            error_message)
        await self.disconnect(session_id)

    async def process_stomp_message(self, message: str, ws: WebSocket, session_id: str) -> None:
        self.session_id_to_last_transmission_date[session_id] = current_datetime()
        logger.info("<<< " + str(message).replace("\n", " // "))

        if message == STOMP_BYTE_LF:
            return

        frame = Frame.unmarshall_single(message)

        if frame.command == STOMP_COMMAND_CONNECT:
            self.session_id_to_connections[session_id] = ws

            if STOMP_HEADER_KEY_TOKEN not in frame.headers:
                await self._send_error_and_close_connection(
                    session_id, f"Required header {STOMP_HEADER_KEY_TOKEN} missing")
                return
            try:
                decode_jwt(frame.headers[STOMP_HEADER_KEY_TOKEN])
            except ExpiredSignatureError:
                await self._send_error_and_close_connection(
                    session_id, "Expired token")
                return
            except Exception:
                await self._send_error_and_close_connection(
                    session_id, "Invalid token")
                return
            if STOMP_HEADER_KEY_ACCEPT_VERSION not in frame.headers:
                await self._send_error_and_close_connection(
                    session_id, f"Required header {STOMP_HEADER_KEY_ACCEPT_VERSION} missing")
                return
            if STOMP_PROTOCOL_VERSION not in frame.headers[STOMP_HEADER_KEY_ACCEPT_VERSION].split(","):
                await self._send_error_and_close_connection(
                    session_id, f"Supported protocol versions are {STOMP_HEADER_KEY_ACCEPT_VERSION}")
                return
            # if STOMP_HEADER_KEY_HOST not in frame.headers:
            #     await StompUtils.send_error_and_close_connection(
            #         ws, f"Required header {STOMP_HEADER_KEY_HOST} missing")
            #     return
            # FIXME: check host

            header = {
                STOMP_HEADER_KEY_SESSION: session_id,
                STOMP_HEADER_KEY_VERSION: STOMP_PROTOCOL_VERSION,
                STOMP_HEADER_KEY_HEART_BEAT: f"{STOMP_HEART_BEAT_PARAM_SX},{STOMP_HEART_BEAT_PARAM_SY}"
            }

            if STOMP_HEADER_KEY_HEART_BEAT in frame.headers:
                heart_beat_parameters = frame.headers[STOMP_HEADER_KEY_HEART_BEAT].split(",")
                if len(heart_beat_parameters) != 2:
                    await self._send_error_and_close_connection(
                        session_id, f"Invalid header with key {STOMP_HEADER_KEY_HEART_BEAT}")
                    return
                try:
                    cx = int(heart_beat_parameters[0])
                    cy = int(heart_beat_parameters[1])
                    if cx < 0 or cy < 0:
                        raise ValueError()
                except ValueError:
                    await self._send_error_and_close_connection(
                        session_id, f"Invalid header with key {STOMP_HEADER_KEY_HEART_BEAT}")
                    return
                if cx != 0 and STOMP_HEART_BEAT_PARAM_SY != 0:
                    heart_beat_interval_client_to_server = max(cx, STOMP_HEART_BEAT_PARAM_SY)
                    # noinspection PyAsyncCall
                    asyncio.create_task(
                        self._schedule_heart_beat_checks(session_id, heart_beat_interval_client_to_server))
                if STOMP_HEART_BEAT_PARAM_SX != 0 and cy != 0:
                    heart_beat_interval_server_to_client = max(STOMP_HEART_BEAT_PARAM_SX, cy)
                    # noinspection PyAsyncCall
                    asyncio.create_task(
                        self._schedule_heart_beats(ws, session_id, heart_beat_interval_server_to_client))
            await StompUtils.transmit(ws, STOMP_COMMAND_CONNECTED, header)
        elif frame.command == STOMP_COMMAND_DISCONNECT:
            await self.disconnect(session_id)
        elif frame.command == STOMP_COMMAND_SUBSCRIBE:
            if STOMP_HEADER_KEY_DESTINATION not in frame.headers:
                await self._send_error_and_close_connection(
                    session_id, f"Required header {STOMP_HEADER_KEY_DESTINATION} missing")
                return
            destination = frame.headers[STOMP_HEADER_KEY_DESTINATION]
            # TODO: implement destination check
            # if destination not in STOMP_SUBSCRIPTION_DESTINATIONS:
            #     await StompUtils.send_error_and_close_connection(
            #         ws, f"Subscription destination {destination} does not exist")
            #     return
            if STOMP_HEADER_KEY_ID not in frame.headers:
                await self._send_error_and_close_connection(
                    session_id, f"Required header {STOMP_HEADER_KEY_ID} missing")
                return
            subscription_id = frame.headers[STOMP_HEADER_KEY_ID]
            if session_id in self.session_id_to_subscriptions:
                subscriptions = self.session_id_to_subscriptions[session_id]
                subscription_ids = [subscription.subscription_id for subscription in subscriptions]
                if subscription_id in subscription_ids:
                    await self._send_error_and_close_connection(
                        session_id, f"Subscription with ID {subscription_id} already registered")
                    return
                subscriptions += StompSubscription(session_id, subscription_id, destination)
            else:
                subscriptions = [StompSubscription(session_id, subscription_id, destination)]
            # if STOMP_HEADER_KEY_ACK not in frame.headers:
            #     await StompUtils.send_error_and_close_connection(
            #         ws, f"Required header {STOMP_HEADER_KEY_ACK} missing")
            #     return
            # TODO: handle acknowledgements
            self.session_id_to_subscriptions[session_id] = subscriptions
        elif frame.command == STOMP_COMMAND_UNSUBSCRIBE:
            if STOMP_HEADER_KEY_ID not in frame.headers:
                await self._send_error_and_close_connection(
                    session_id, f"Required header {STOMP_HEADER_KEY_ID} missing")
                return
            subscription_id = frame.headers[STOMP_HEADER_KEY_ID]
            if session_id not in self.session_id_to_subscriptions:
                await self._send_error_and_close_connection(
                    session_id, f"Subscription with ID {subscription_id} does not exist")
                return
            subscriptions = self.session_id_to_subscriptions[session_id]
            subscription_ids = [subscription.subscription_id for subscription in subscriptions]
            if subscription_id not in subscription_ids:
                await self._send_error_and_close_connection(
                    session_id, f"Subscription with ID {subscription_id} does not exist")
                return
            self.session_id_to_subscriptions[session_id] = [subscription for subscription in subscriptions if
                                                            subscription.subscription_id != subscription_id]
        elif frame.command == STOMP_COMMAND_SEND:
            # nothing to handle yet
            return
            # destination = frame.headers[STOMP_HEADER_KEY_DESTINATION]
            # if destination and destination in self.subscriptions:
            #     for client in self.subscriptions[destination]:
            #         await client.send_text(frame.body)
        else:
            logger.warning(f"Unknown STOMP command {frame.command}!")
            await ws.send_text(frame.body)

    async def send_message(self, destination: str, message, content_type=STOMP_HEADER_VALUE_CONTENT_TYPE_JSON):
        for session_id, subscriptions in self.session_id_to_subscriptions.items():
            for subscription in subscriptions:
                if subscription.destination != destination:
                    continue
                # TODO: handle message IDs and acknowledgements
                message_id = str(uuid.uuid4())
                await StompUtils.transmit(
                    self.session_id_to_connections[session_id], STOMP_COMMAND_MESSAGE,
                    {STOMP_HEADER_KEY_SUBSCRIPTION: subscription.subscription_id,
                     STOMP_HEADER_KEY_MESSAGE_ID: message_id, STOMP_HEADER_KEY_DESTINATION: destination,
                     STOMP_HEADER_KEY_CONTENT_TYPE: content_type}, message)

    async def disconnect(self, session_id: str):
        if session_id in self.session_id_to_last_transmission_date:
            self.session_id_to_last_transmission_date.pop(session_id)
        if session_id in self.session_id_to_subscriptions:
            self.session_id_to_subscriptions.pop(session_id)
        if session_id in self.session_id_to_connections:
            try:
                await self.session_id_to_connections[session_id].close()
            finally:
                self.session_id_to_connections.pop(session_id)


stomp_server = StompServer()
