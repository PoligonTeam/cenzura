"""
Copyright 2022-2025 PoligonTeam

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import aiohttp
import asyncio
import re

from typing import TypedDict, Literal, Optional

THINK_REGEX = re.compile(r"(<think>)?(.|\n)*<\/think>\n")

Model = Literal[
    "distil-whisper-large-v3-en",
    "gemma2-9b-it",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "llama-guard-3-8b",
    "llama3-70b-8192",
    "llama3-8b-8192",
    "mixtral-8x7b-32768",
    "whisper-large-v3",
    "whisper-large-v3-turbo",
    "qwen-2.5-32b",
    "deepseek-r1-distill-qwen-32b",
    "deepseek-r1-distill-llama-70b-specdec",
    "deepseek-r1-distill-llama-70b",
    "llama-3.3-70b-specdec",
    "llama-3.2-1b-preview",
    "llama-3.2-3b-preview",
    "llama-3.2-11b-vision-preview",
    "llama-3.2-90b-vision-preview"
]

class Message(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str

class ChatData(TypedDict):
    model: Model
    messages: list[Message]

class Groq:
    URL = "https://api.groq.com/openai/v1"
    API_KEY_COUNTER = 0

    def __init__(self, api_keys: list[str], model: Model, system_message: Optional[str] = None, seed: int = -1, max_messages: int = 20, *, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        self.loop = loop or asyncio.get_event_loop()
        self.session = aiohttp.ClientSession()
        self.api_keys = api_keys
        self.model = model
        self.system_message = system_message
        self.seed = seed
        self.max_messages = max_messages
        self.messages: list[Message] = []

    def __del__(self) -> None:
        self.loop.create_task(self.session.close())

    @property
    def api_key(self) -> str:
        api_key = self.api_keys[Groq.API_KEY_COUNTER % len(self.api_keys)]
        Groq.API_KEY_COUNTER += 1
        return api_key

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": "Bearer " + self.api_key}

    def get_message(self, content: str) -> ChatData:
        message: Message = {"role": "user", "content": content}

        if len(self.messages) > self.max_messages:
            self.messages = self.messages[:self.max_messages-1]

        self.messages.append(message)

        if self.system_message:
            self.messages = [Message(
                role = "system",
                content = self.system_message
            )] + self.messages

        return {
            "model": self.model,
            "messages": self.messages
        }

    async def chat(self, content: str) -> str:
        async with self.session.post(Groq.URL + "/chat/completions", headers=self.headers, json=self.get_message(content)) as response:
            data = await response.json()

            self.messages.extend([choice["message"] for choice in data["choices"]])

            result = self.messages[-1]["content"]
            result = THINK_REGEX.sub("", result)
            result = result.replace("<think>", "")

            return result