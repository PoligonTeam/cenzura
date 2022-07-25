import asyncio

class Typing:
    def __init__(self, message):
        self.loop = asyncio.get_event_loop()
        self.message = message

    async def do_typing(self):
        while True:
            await asyncio.sleep(5)
            await self.message.channel.start_typing()

    def start(self):
        return self.__aenter__()

    def stop(self):
        return self.__aexit__(None, None, None)

    async def __aenter__(self):
        await self.message.channel.start_typing()
        self.task = self.loop.create_task(self.do_typing())

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.task.cancel()