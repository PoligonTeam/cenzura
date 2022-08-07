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

from enum import Enum, EnumMeta
import string

string_chars = string.ascii_letters + string.digits + "_"

class EnumMeta(EnumMeta):
    def __contains__(cls, item):
        return item in [v.value for v in cls.__members__.values()]

class Tokens(Enum, metaclass=EnumMeta):
    LEFT_CURLY_BACKET = "{"
    RIGHT_CURLY_BACKET = "}"
    LEFT_BRACKET = "("
    RIGHT_BRACKET = ")"
    COMMA = ","
    DOT = "."
    COLON = ":"
    PLUS = "+"
    MINUS = "-"
    MULTIPLY = "*"
    DIVIDE = "/"
    MODULO = "%"
    ASSIGN = "="
    EQUALS = "=="
    NOTEQUALS = "!="
    GREATER = ">"
    LOWER = "<"
    COMMENT = "#"
    NEWLINE = "\n"

class Keywords(Enum, metaclass=EnumMeta):
    AND = "and"
    OR = "or"
    RETURN = "return"

class Types(Enum, metaclass=EnumMeta):
    VAR = "var"
    STR = "str"
    INT = "int"
    BOOL = "bool"
    LIST = "list"
    DICT = "dict"
    UNKNOWN = "unknown"

class Token:
    def __init__(self, _type: Types, value = ""):
        self.type = _type
        self.value = value
    def __iadd__(self, item):
        self.value += item
        return self
    def __str__(self):
        return f"<{self.type}: {self.value!r}>"
    def __repr__(self):
        return f"<{self.type}: {self.value!r}>"

class Lexer:
    def __init__(self, text = ""):
        self.text = text
        self.position = 0

    def make_int(self):
        token = Token(Types.INT)

        while True:
            if self.position >= len(self.text):
                break

            current_char = self.text[self.position]

            if current_char in string.digits:
                token += current_char
            else:
                break

            self.position += 1

        return token

    def make_string(self):
        token = Token(Types.VAR)

        while True:
            if self.position >= len(self.text):
                break

            current_char = self.text[self.position]

            if current_char == "\"":
                token.type = Types.STR

                while True:
                    self.position += 1

                    if self.position >= len(self.text):
                        break

                    if self.text[self.position] == "\"":
                        break
                    else:
                        token += self.text[self.position]
            elif current_char in string_chars:
                token += current_char
            else:
                break

            self.position += 1

        if token.value in Keywords:
            token = Keywords(token.value)
        elif token.value in ["true", "false"]:
            token = Token(Types.BOOL, token.value)

        return token

    def make_tokens(self):
        tokens = []

        while True:
            if self.position >= len(self.text):
                break

            current_char = self.text[self.position]

            if self.text[self.position:self.position + 2] in Tokens:
                tokens.append(Tokens(self.text[self.position:self.position + 2]))
                self.position += 1
            elif current_char in Tokens:
                tokens.append(Tokens(current_char))
            elif current_char in Keywords:
                tokens.append(Keywords(current_char))
            elif current_char in string.digits:
                tokens.append(self.make_int())
                continue
            elif current_char in string_chars:
                tokens.append(self.make_string())
                continue
            elif current_char in "\"":
                tokens.append(self.make_string())
                continue

            self.position += 1

        self.position = 0

        return tokens