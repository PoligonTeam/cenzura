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

from .lexer import Lexer, Tokens, Keywords, Types, Token
from types import CoroutineType
import random, datetime, re, string, json

class List(list):
    def __init__(self, *args):
        super().__init__(args)

    def has(self, item):
        return item in self

    def get(self, index):
        return self[index] if index < len(self) else False

    def remove(self, item):
        if item in self:
            self.remove(item)
            return True
        return False

class Dict(dict):
    def __init__(self, **kwargs):
        super().__init__(kwargs)

    def __str__(self):
        return json.dumps(self, indent=4, default=str)

    def __getattribute__(self, name):
        if name in self:
            return self[name]

        return super().__getattribute__(name)

    def has(self, item):
        return item in self

    def get(self, item):
        return self[item] if item in self else None

    def set(self, key, value):
        self[key] = value
        return True

    def items(self):
        return [(key, self[key]) for key in self]

    def keys(self):
        return [key for key, _ in self.items()]

    def values(self):
        return [value for _, value in self.items()]

    def remove(self, item):
        if item in self:
            self.pop(item)
            return True
        return False

def _len(obj):
    if not hasattr(obj, "__len__"):
        return False

    return len(obj)

class Parser:
    def __init__(self, lexer: Lexer, *, modules = {}, builtins = {}, variables = {}):
        self.lexer = lexer
        self.tokens = self.lexer.make_tokens()
        self.position = 0
        self.modules = {
            **modules,
            "random": {
                "builtins": {
                    "random_int": random.randint,
                    "random_choice": lambda *args: random.choice(args[0] if len(args) == 1 else args)
                }
            },
            # "regex": {
            #     "builtins": {
            #         "match": lambda pattern, string: not not re.match(pattern, string),
            #         "find": lambda pattern, string, index = 0: (re.findall(pattern, string) or [False])[index],
            #         "find_all": lambda pattern, string, join_string = "": join_string.join(re.findall(pattern, string)) or False
            #     }
            # },
            "date": {
                "builtins": {
                    "now": lambda format = r"%Y-%m-%d %H:%M:%S": datetime.datetime.now().strftime(format),
                    "timestamp": lambda: int(datetime.datetime.now().timestamp()),
                    "from_timestamp": lambda timestamp, format = r"%Y-%m-%d %H:%M:%S": datetime.datetime.fromtimestamp(timestamp).strftime(format)
                }
            },
            "string": {
                "variables": {
                    "whitespace": string.whitespace,
                    "ascii_lowercase": string.ascii_lowercase,
                    "ascii_uppercase": string.ascii_uppercase,
                    "ascii_letters": string.ascii_letters,
                    "digits": string.digits,
                    "hexdigits": string.hexdigits,
                    "octdigits": string.octdigits,
                    "punctuation": string.punctuation,
                    "printable": string.printable
                }
            }
        }
        self.builtins = {
            **builtins,
            "str": str,
            "int": int,
            "list": List,
            "dict": Dict,
            "len": _len,
            "hex": lambda hexadecimal: int(hexadecimal, 16),
            "bin": lambda binary: int(binary, 2),
            "chr": chr,
            "ord": ord,
            "contains": lambda _object, item: item in _object
        }
        self.variables = variables

    def convert(self, position, var = True):
        if var and self.tokens[position].type is Types.VAR:
            return self.variables[self.tokens[position].value]
        elif self.tokens[position].type is Types.BOOL:
            return self.tokens[position].value == "true"
        elif self.tokens[position].type is Types.INT:
            return int(self.tokens[position].value)
        elif var is False or self.tokens[position].type in (Types.STR, Types.LIST, Types.DICT, Types.UNKNOWN):
            return self.tokens[position].value

    def set(self, result, position = None, position2 = None):
        position = position or self.position
        position2 = position2 or position + 2
        self.tokens[position - 1] = result
        del self.tokens[position:position2]
        self.position = 0

    async def parse(self):
        result = None

        math_operators = {
            Tokens.PLUS: "__add__",
            Tokens.MINUS: "__sub__",
            Tokens.MULTIPLY: "__mul__",
            Tokens.DIVIDE: "__truediv__",
            Tokens.MODULO: "__mod__"
        }

        comparison_operators = {
            Tokens.EQUALS: "__eq__",
            Tokens.NOTEQUALS: "__ne__",
            Tokens.GREATER: "__gt__",
            Tokens.LESS: "__lt__"
        }

        types = {
            str: Types.STR,
            int: Types.INT,
            bool: Types.BOOL,
            list: Types.LIST,
            dict: Types.DICT,
        }

        while True:
            if self.position >= len(self.tokens):
                break

            current_token = self.tokens[self.position]

            if current_token is Tokens.ASSIGN:
                if isinstance(self.tokens[self.position + 1], Token) and self.tokens[self.position + 1].type is Types.VAR:
                    if not isinstance(self.tokens[self.position + 1].value, (list, dict)) and self.tokens[self.position + 1].value in self.builtins or (self.tokens[self.position + 1].value in self.variables and self.tokens[self.position + 2] is Tokens.DOT):
                        self.position += 1
                        continue

                self.variables[self.tokens[self.position - 1].value] = self.convert(self.position + 1)
                self.position += 1
            elif current_token.value in Tokens:
                if current_token is Tokens.COMMENT:
                    while True:
                        if self.position >= len(self.tokens):
                            break
                        if self.tokens[self.position] is Tokens.NEWLINE:
                            break
                        self.position += 1
                elif current_token is Tokens.NEWLINE:
                    self.position += 1
                    continue
                elif current_token in math_operators:
                    _result = getattr(self.convert(self.position - 1), math_operators[current_token])(self.convert(self.position + 1))
                    if isinstance(_result, str):
                        _type = Types.STR
                    elif isinstance(_result, (int, float)):
                        _type = Types.INT
                        _result = int(_result)
                    self.set(Token(_type, _result))
                    continue
                elif current_token in comparison_operators:
                    self.set(Token(Types.BOOL, "true" if getattr(self.convert(self.position - 1), comparison_operators[current_token])(self.convert(self.position + 1)) is True else "false"))
                    continue
                elif current_token is Tokens.LEFT_CURLY_BRACKET:
                    if self.tokens[self.position - 1].type is Types.VAR:
                        self.tokens[self.position - 1] = Token(Types.BOOL, ["false", "true"][bool(self.variables[self.tokens[self.position - 1].value])])

                    if self.tokens[self.position - 1].type is Types.BOOL and self.tokens[self.position - 1].value == "false":
                        self.position += 1
                        while True:
                            if self.position >= len(self.tokens):
                                break
                            if self.tokens[self.position] is Tokens.RIGHT_CURLY_BRACKET:
                                self.position += 1
                                break
                            self.position += 1
                        continue
            elif current_token.value in Keywords:
                if current_token is Keywords.IMPORT:
                    module = self.modules[self.tokens[self.position + 1].value]
                    if "builtins" in module:
                        self.builtins = {**module["builtins"], **self.builtins}
                    if "variables" in module:
                        self.variables = {**module["variables"], **self.variables}
                elif current_token is Keywords.RETURN:
                    if self.position + 2 < len(self.tokens):
                        self.position += 1
                        continue

                    result = self.convert(self.position + 1)
                    break
                elif current_token is Keywords.AND:
                    self.set(Token(Types.BOOL, "true" if self.convert(self.position - 1) and self.convert(self.position + 1) else "false"))
                    continue
                elif current_token is Keywords.OR:
                    self.set(Token(Types.BOOL, "true" if self.convert(self.position - 1) or self.convert(self.position + 1) else "false"))
                    continue
            elif isinstance(current_token.value, str) and current_token.value in self.builtins:
                args = []
                kwargs = {}
                close_position = None
                _continue = False

                if current_token.value in self.builtins:
                    _object = self.builtins.get(current_token.value)
                elif current_token.value in self.variables:
                    _object = self.variables.get(current_token.value)

                if self.tokens[self.position + 1] is Tokens.DOT:
                    _object = getattr(_object, self.tokens[self.position + 2].value)
                    self.position += 2

                if self.tokens[self.position + 1] is Tokens.LEFT_BRACKET:
                    for position in range(self.position + 2, len(self.tokens)):
                        if self.tokens[position] is Tokens.RIGHT_BRACKET:
                            close_position = position
                            break
                        elif self.tokens[position] is Tokens.COMMA:
                            continue
                        elif self.tokens[position] is Tokens.COLON:
                            if self.tokens[position + 1].type is Types.VAR:
                                if self.tokens[position + 2] is Tokens.DOT:
                                    self.position = position + 1
                                    _continue = True
                                    break
                                kwargs[self.tokens[position - 1].value] = self.variables[self.tokens[position + 1].value]
                            else:
                                kwargs[self.tokens[position - 1].value] = self.convert(position + 1)
                            continue
                        elif self.tokens[position].type.value in Types and self.tokens[position - 1] is not Tokens.COLON:
                            if self.tokens[position + 1] is Tokens.DOT:
                                self.position = position
                                _continue = True
                                break
                            if self.tokens[position].type is Types.VAR:
                                if self.tokens[position].value in self.variables:
                                    args.append(self.variables[self.tokens[position].value])
                            else:
                                args.append(self.convert(position))
                            continue

                    if _continue is True:
                        continue

                    _type = Types.UNKNOWN
                    _result = _object(*args, **kwargs)

                    if isinstance(_result, CoroutineType):
                        _result = await _result
                    elif type(_result) in types:
                        _type = types[type(_result)]

                        if _type is Types.BOOL:
                            _result = ["false", "true"][_result]

                    if self.tokens[self.position - 1] is Tokens.DOT:
                        self.position -= 2

                    self.set(Token(_type, _result), self.position + 1, close_position + 1)

                    self.position = 0
                    continue
            elif isinstance(current_token.value, str) and current_token.value in self.variables and self.tokens[self.position + 1] is Tokens.DOT:
                _object = False
                item = self.convert(self.position + 2, False)

                if isinstance(self.variables[current_token.value], dict):
                    if item in self.variables[current_token.value]:
                        _object = self.variables[current_token.value][item]
                elif isinstance(self.variables[current_token.value], list):
                    if item < len(self.variables[current_token.value]):
                        _object = self.variables[current_token.value][item]
                else:
                    _object = getattr(self.variables[current_token.value], self.tokens[self.position + 2].value, False)

                _type = Types.UNKNOWN

                if isinstance(_object, str):
                    _type = Types.STR
                elif isinstance(_object, bool):
                    _type = Types.BOOL
                    _object = ["false", "true"][_object]
                elif isinstance(_object, int):
                    _type = Types.INT
                elif isinstance(_object, list):
                    _type = Types.LIST
                elif isinstance(_object, dict):
                    _type = Types.DICT

                self.set(Token(_type, _object), self.position + 1, self.position + 3)

                self.position = 0
                continue

            self.position += 1

        self.position = 0

        return result