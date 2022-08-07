"""
Copyright 2022 PoligonTeam

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

from . import run
import asyncio, sys, os.path

async def main(file):
    builtins = {
        "print": print,
        "input": input
    }

    if file is not None:
        if os.path.isdir(file) is True:
            file += "/__main__.cscript"

        with open(file, "r") as file:
            return await run(file.read(), builtins=builtins)

    code = ""

    while True:
        code += input(">>> ") + "\n"

        if code.splitlines()[-1] == "":
            result = await run(code[:-2], builtins=builtins)

            if result is not None:
                print(result)

            code = ""

if __name__ == "__main__":
    try:
        asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else None))
    except KeyboardInterrupt:
        pass