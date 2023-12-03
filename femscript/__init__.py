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

from .lexer import Lexer
from .parser import Parser, Dict, List

async def run(code, *, modules = {}, builtins = {}, variables = {}):
    parser = Parser(Lexer(code), modules=modules, builtins=builtins, variables=variables)

    return await parser.parse()

from femscript_rs import *
from typing import List, Type, Literal, Optional, Union, TypedDict, Callable
import asyncio

types = {
    "Str": str,
    "Int": float,
    "Bool": bool,
    "None": type(None),
    "List": list,
    "Scope": dict
}

class Token(TypedDict):
    type: str
    value: str
    number: float
    list: List["Token"]
    scope: Optional[List["Variable"]]
    pyobject: Optional[object]

class AST(TypedDict):
    type: str
    token: Token
    children: List["AST"]

class Variable(TypedDict):
    name: str
    value: Token

class Function(TypedDict):
    name: str
    func: Callable[[List[Token], List[Variable]], None]

def var(name: str, value: object = None, *, variables: List[Variable] = None) -> Variable:
    if variables is not None:
        token = Femscript.to_fs({})

        for variable in variables:
            token["scope"].append(variable)

        return Variable(name=name, value=token)

    variable = Variable(name=name, value=Femscript.to_fs(value))

    return variable

class FemscriptException(Exception):
    pass

class Femscript:
    def __init__(self, code: str, *, variables: List[Variable] = None, functions: List[Callable[[str, List[Token], List[Variable]], Token]] = None) -> None:
        self.code = code
        self.tokens = generate_tokens(code)
        self.ast = generate_ast(self.tokens)

        self.variables = variables or []
        self.functions = functions or []

    @classmethod
    def py_type(cls, fs_type: Literal["Str", "Int", "Bool", "None", "List", "Scope"]) -> Type:
        return types.get(fs_type, type(None))

    @classmethod
    def fs_type(cls, obj: object) -> str:
        return {**{value: key for key, value in types.items()}, int: "Int"}.get(type(obj), "PyObject")

    @classmethod
    def to_fs(cls, obj: object) -> Token:
        token = Token(
            type = _type if (_type := cls.fs_type(obj)) else "PyObject",
            value = "",
            number = 0.0,
            list = []
        )

        token[result[0]] = (result := {
            "Str": lambda: ("value", obj),
            "Int": (_int := lambda: ("number", float(obj))),
            "Bool": _int,
            "List": lambda: ("list", [cls.to_fs(obj) for obj in obj]),
            "None": lambda: ("type", "None"),
            "Scope": lambda: ("scope", [{"name": key, "value": cls.to_fs(value)} for key, value in obj.items()])
        }.get(_type, lambda: ("pyobject", obj))())[1]

        return token

    @classmethod
    def to_py(cls, token: Token) -> object:
        if "Error" in token["type"]:
            return FemscriptException(token["value"])

        return {
            "Str": (_str := lambda: token["value"]),
            "Int": lambda: n if not (n := token["number"]).is_integer() else n // 1,
            "Bool": lambda: bool(token["number"]),
            "List": lambda: [cls.to_py(token) for token in token["list"]],
            "None": lambda: None,
            "Scope": lambda: {name: cls.to_py(token) for name, token in token.get("scope", {}).items()},
            "PyObject": lambda: token["pyobject"]
        }.get(token["type"], _str)()

    @classmethod
    def error(cls, error: str) -> Token:
        return Token(
            type = "Error",
            value = "Error: " + error,
            number = 0.0,
            list = []
        )

    def wrap_function(self, func: Callable[..., object] = None, *, func_name: str = None, with_name: bool = False) -> object:
        def wrapper(func: Callable[..., object]):
            if asyncio.iscoroutinefunction(func) == True:
                def wrapper(name: str, args: Union[List[Token], Token], scope: List[Variable]) -> Token:
                    async def wrapper():
                        try:
                            if not isinstance(args, tuple) and args["type"] == "Scope":
                                return self.to_fs(
                                    await func(*((name,) if with_name is True else ()), **self.to_py(args))
                                )

                            return self.to_fs(
                                await func(*((name,) if with_name is True else ()), *(self.to_py(arg) for arg in args))
                            )
                        except FemscriptException as exc:
                            return self.error(str(exc))

                    return self.to_fs(wrapper())
            else:
                def wrapper(name: str, args: Union[List[Token], Token], scope: List[Variable]) -> Token:
                    try:
                        if not isinstance(args, tuple) and args["type"] == "Scope":
                            return self.to_fs(
                                func(*((name,) if with_name is True else ()), **self.to_py(args))
                            )

                        return self.to_fs(
                            func(*((name,) if with_name is True else ()), *(self.to_py(arg) for arg in args))
                        )
                    except FemscriptException as exc:
                        return self.error(str(exc))

            self.functions.append(
                Function(
                    name = func_name or func.__name__,
                    func = wrapper
                )
            )

            return wrapper

        if func is not None:
            return wrapper(func)

        return wrapper

    async def execute(self, *, memory_limit: int = 1024 * 1024 * 1024, max_variables: int = 1000, max_depth: int = 1000, frame_function: Callable[[Variable], Token] = None, debug: bool = False) -> object:
        return self.to_py(await execute_ast(self.ast, self.variables, self.functions, debug))