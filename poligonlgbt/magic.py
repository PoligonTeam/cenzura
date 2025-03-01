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

from ctypes import *
from ctypes.util import find_library

EXTENSION_FLAG = 0x1000000

lib = cdll.LoadLibrary(find_library("magic"))

lib.magic_open.restype = c_void_p
lib.magic_open.argtypes = [c_int]
lib.magic_load.restype = c_int
lib.magic_load.argtypes = [c_void_p, c_char_p]
lib.magic_buffer.restype = c_char_p
lib.magic_buffer.argtypes = [c_void_p, c_void_p, c_size_t]
lib.magic_close.argtypes = [c_void_p]

def get_extension(content: bytes) -> str:
    magic = lib.magic_open(EXTENSION_FLAG)
    lib.magic_load(magic, None)
    extension = lib.magic_buffer(magic, content, len(content))
    lib.magic_close(magic)

    extension = extension.decode("utf-8").split("/")[0]

    extensions = {
        "jpeg": "jpg",
        "???": "txt"
    }

    return extensions.get(extension, extension)