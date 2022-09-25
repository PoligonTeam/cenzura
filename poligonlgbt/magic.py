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
    return extension.decode("utf-8").split("/")[0]