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

import asyncio, uvloop, config

from dashboard.server import Server

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

def main() -> None:
    loop.create_task((server := Server(loop)).run(host=config.DASHBOARD_HOST, port=config.DASHBOARD_PORT))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()
        loop.close()

if __name__ == "__main__":
    main()