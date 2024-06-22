"""
Copyright 2023-2024 czubix

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

import asyncio, socket, pickle, struct, uuid
from pathlib import Path
from enum import Enum
from typing import Union, Callable

class OpCodes(Enum):
    EMIT = 0
    RESPONSE = 1

class Client:
    def __init__(self, sock: "IPC", name: str, path: Path) -> None:
        self.socket = sock

        self.name = name
        self.path = path

    def get_packet[T](self, opcode: OpCodes, nonce: bytes, event: str, data: bytes) -> bytes:
        return struct.pack("H16sHI", opcode.value, nonce, len(event), len(data))

    async def emit[T, U](self, event: str, data: T = None, *, wait_for_response: bool = None) -> U:
        wait_for_response = wait_for_response or True
        data = pickle.dumps(data)
        nonce = uuid.uuid4().bytes

        try:
            self.socket.sendto(self.get_packet(OpCodes.EMIT, nonce, event, data), self.path.as_posix())
            self.socket.sendto(event.encode() + data, self.path.as_posix())
        except ConnectionRefusedError:
            return

        if wait_for_response is True:
            for _ in range(300):
                if nonce in self.socket.responses:
                    return self.socket.responses.pop(nonce)
                await asyncio.sleep(0.1)

    def respond[T](self, event: str, nonce: bytes, data: T) -> None:
        data = pickle.dumps(data)

        try:
            self.socket.sendto(self.get_packet(OpCodes.RESPONSE, nonce, event, data), self.path.as_posix())
            self.socket.sendto(event.encode() + data, self.path.as_posix())
        except ConnectionRefusedError:
            return

class IPC(socket.socket):
    PATH = Path("/tmp/femipc")

    def __init__(self, name: str, clients: Union[list[str], str], *, loop: asyncio.AbstractEventLoop = None) -> None:
        super().__init__(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.setblocking(False)

        self.loop = loop or asyncio.get_event_loop()

        self.name = name
        self.file = self.PATH / (self.name + ".sock")

        self._clients = [Client(self, name, self.PATH / (name + ".sock")) for name in (clients if isinstance(clients, list) else [clients])]

        if not self.PATH.exists():
            self.PATH.mkdir()
        if self.file.exists():
            self.file.unlink()

        self.bind(self.file.as_posix())

        self.events = {}
        self.responses = {}

        self.receiver_task = self.loop.create_task(self.receiver())

    @property
    def clients(self) -> list[Client]:
        return self._clients

    def add_client(self, name: str) -> Client:
        client = Client(self, name, self.PATH / (name + ".sock"))
        self._clients.append(client)
        return client

    def get_client(self, *, name: str = None, path: str = None) -> Client:
        for client in self.clients:
            if (name and client.name == name) or (path and client.path == Path(path)):
                return client

    def on[T](self, event: str) -> Callable[[T], object]:
        def wrapper[U](func: T) -> U:
            self.events[event] = func
            return func
        return wrapper

    async def emit[T, U](self, event: str, data: T) -> U:
        if event not in self.events:
            raise Exception("event not found")
        return await self.events[event](data)

    async def receive[T](self) -> tuple[str, OpCodes, bytes, str, T]:
        while True:
            try:
                data, path = self.recvfrom(24)
                opcode, nonce, event_length, data_length = struct.unpack("H16sHI", data)
                opcode = OpCodes(opcode)

                while True:
                    try:
                        received = self.recvfrom(event_length + data_length)[0]
                        received_event = received[:event_length].decode()
                        received_data = pickle.loads(received[event_length:])

                        return path, opcode, nonce, received_event, received_data
                    except socket.error:
                        await asyncio.sleep(0.1)
            except socket.error:
                await asyncio.sleep(0.1)

    async def receiver(self) -> None:
        while True:
            path, opcode, nonce, received_event, received_data = await self.receive()

            if opcode == OpCodes.EMIT:
                result = await self.emit(received_event, received_data)
                client = self.get_client(path=path)
                client.respond(received_event, nonce, result)
            elif opcode == OpCodes.RESPONSE:
                self.responses[nonce] = received_data

            await asyncio.sleep(0.1)

    def close(self) -> None:
        super().close()
        self.file.unlink()