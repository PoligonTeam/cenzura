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
    EVENT = 0
    MESSAGE = 1

class Client:
    def __init__(self, sock: socket.socket, name: str, path: Path) -> None:
        self.socket = sock

        self.name = name
        self.path = path

    def get_packet[T](self, opcode: OpCodes, event: str, data: bytes) -> bytes:
        return struct.pack("HHI", opcode.value, len(event), len(data))

    def emit[T](self, event: str, data: T) -> None:
        data = pickle.dumps(data)

        try:
            self.socket.sendto(self.get_packet(OpCodes.EVENT, event, data), self.path.as_posix())
            self.socket.sendto(event.encode() + data, self.path.as_posix())
        except ConnectionRefusedError:
            return

    async def send[T, U](self, data: T) -> U:
        data = pickle.dumps(data)
        nonce = uuid.uuid4().bytes

        try:
            self.socket.sendto(self.get_packet(OpCodes.MESSAGE, nonce, data), self.path.as_posix())
            self.socket.sendto(nonce + data, self.path.as_posix())
        except ConnectionRefusedError:
            return

        with self.socket:
            for _ in range(3):
                received_event, received_data = await self.socket.recv()

                if nonce != received_event:
                    await self.socket.emit(received_event, received_data)
                    continue

                return received_data

class IPC(socket.socket):
    PATH = Path("/tmp/femipc")

    def __init__(self, name: str, clients: Union[list[str], str], *, loop: asyncio.AbstractEventLoop = None) -> None:
        super().__init__(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.setblocking(False)

        self.loop = loop or asyncio.get_event_loop()
        self._lock = False

        self.name = name
        self.file = self.PATH / (self.name + ".sock")

        self._clients = [Client(self, name, self.PATH / (name + ".sock")) for name in (clients if isinstance(clients, list) else [clients])]

        if not self.PATH.exists():
            self.PATH.mkdir()
        if self.file.exists():
            self.file.unlink()

        self.bind(self.file.as_posix())

        self.events = {}

        self.receiver_task = self.loop.create_task(self.receiver())

    def __enter__(self) -> None:
        self._lock = True

    def __exit__(self) -> None:
        self._lock = False

    @property
    def clients(self) -> list[Client]:
        return self._clients

    def add_client(self, name: str) -> Client:
        client = Client(self, name, self.PATH / (name + ".sock"))
        self._clients.append(client)
        return client

    def on[T](self, event: str) -> Callable[[T], object]:
        def wrapper[U](func: T) -> U:
            self.events[event] = func
            return func
        return wrapper

    async def emit[T](self, event: str, data: T) -> None:
        if event not in self.events:
            raise Exception("event not found")
        await self.events[event](data)

    async def recv[T](self) -> tuple[str, T]:
        while True:
            try:
                opcode, event_length, data_length = struct.unpack("HHI", self.recvfrom(8)[0])
                opcode = OpCodes(opcode)

                received = self.recvfrom(event_length + data_length)[0]
                received_event = received[:event_length].decode()
                received_data = pickle.loads(received[event_length:data_length+1])

                return received_event, received_data
            except socket.error:
                await asyncio.sleep(0)

    async def receiver(self) -> None:
        while True:
            if self._lock: continue
            await self.emit(*await self.recv())
            await asyncio.sleep(0)

    def close(self) -> None:
        super().close()
        self.file.unlink()