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

import requests

from model.client.ollama.generate_chat_completion_response import GenerateChatCompletionResponse
from service.environment import ollama_url


class OllamaApi:
    @staticmethod
    def chat(messages):
        json = {"model": "llama2", "messages": messages, "stream": False}
        response = GenerateChatCompletionResponse().model_validate(
            requests.post(f"{ollama_url()}/api/chat", json=json))
        return response.message
