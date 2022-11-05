import asyncio
from .types import Message

class Typing:
    def __init__(self, message: Message):
        self.loop = asyncio.get_event_loop()
        self.message = message

    def send(self):
        return self.message.channel.start_typing()

    async def do_typing(self):
        for _ in range(12):
            await asyncio.sleep(5)
            await self.send()

    def start(self):
        return self.__aenter__()

    def stop(self):
        return self.__aexit__(None, None, None)

    async def __aenter__(self):
        await self.send()
        self.task = self.loop.create_task(self.do_typing())

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.task.cancel()