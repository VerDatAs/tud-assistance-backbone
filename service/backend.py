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
from typing import List

from model.api.assistance import Assistance as AssistanceSchema
from model.api.assistance_bundle import AssistanceBundle
from model.core.tutorial_module import Assistance
from service.stomp import stomp_server, STOMP_SUBSCRIPTION_DESTINATION_ASSISTANCE


def send_assistance(assistance_list: List[Assistance]):
    if assistance_list is None:
        return

    assistance_bundle = AssistanceBundle(
        assistance=list(
            map(
                lambda assistance: AssistanceSchema.model_validate(
                    assistance.to_dict()
                ),
                assistance_list,
            )
        )
    )

    asyncio.create_task(stomp_server.send_message(
        STOMP_SUBSCRIPTION_DESTINATION_ASSISTANCE, assistance_bundle.model_dump_json(by_alias=True)))
