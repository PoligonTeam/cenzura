#!/usr/bin/python3

import femscript
from enum import Enum
import sys

counter = 0

def count(reset=False):
    global counter
    if reset:
        counter = 0
    old = counter
    counter += 1
    return old

class TokenType(Enum):
    UNKNOWN = count()

    LEFT_CURLY_BRACKET = count()
    RIGHT_CURLY_BRACKET = count()
    LEFT_BRACKET = count()
    RIGHT_BRACKET = count()
    COMMA = count()
    DOT = count()
    COLON = count()
    PLUS = count()
    MINUS = count()
    MULTIPLY = count()
    DIVIDE = count()
    MODULO = count()
    ASSIGN = count()
    NOT = count()
    GREATER = count()
    LESS = count()
    COMMENT = count()
    NEWLINE = count()

    IF = count()
    ELSE = count()
    AND = count()
    OR = count()
    FN = count()
    IMPORT = count()
    RETURN = count()

    VAR = count()
    STR = count()
    INT = count()
    BOOL = count()
    LIST = count()
    DICT = count()

    ERROR = count()
    UNDEFINED = count()
    SYNTAX_ERROR = count()
    TYPE_ERROR = count()

class Token:
    def __init__(self, _type, value):
        self.type = TokenType(_type)

        if value:
            value = value.replace("\n", "\\n")

        self.value = value

    def __str__(self):
        return f"<{self.type.name}> {self.value}"

    def __repr__(self):
        return f"<{self.type.name}> {self.value}"

def code_from_tokens(tokens):
    if not tokens:
        return "code   1 :"

    code = []

    for token in tokens:
        if token.type == TokenType.IF:
            code.append("if ")
        elif token.type == TokenType.ELSE:
            code.append(" else ")
        elif token.type == TokenType.AND:
            code.append(" and ")
        elif token.type == TokenType.OR:
            code.append(" or ")
        elif token.type == TokenType.IMPORT:
            code.append("import ")
        elif token.type == TokenType.RETURN:
            code.append("return ")
        elif token.type == TokenType.LEFT_CURLY_BRACKET:
            code.append(" {")
        elif token.type == TokenType.RIGHT_CURLY_BRACKET:
            code.append("} ")
        elif token.type == TokenType.NEWLINE:
            if not code[-1] == "\n":
                code.append("\n")
        elif token.type == TokenType.STR:
            code.append("\"" + token.value + "\"")
        else:
            code.append(token.value)

    parsed_code = "code   1 : "
    line = 2

    for token in code:
        if token == "\n":
            parsed_code += "\n" + " " * 7 + "%d : " % line
            line += 1
        else:
            parsed_code += token

    return parsed_code

def parse_tokens(tokens):
    if not tokens:
        return "tokens 1 :"

    text = "tokens 1 : ["
    line = 2

    for token in tokens:
        if token.type == TokenType.NEWLINE:
            if not text[-1] == "\n":
                text += "\n"
        else:
            text += str(token) + ", "

    text = text[:-2] + "]"

    parsed_tokens = ""

    for char in text:
        if char == "\n":
            parsed_tokens += "\n" + " " * 7 + "%d : " % line
            line += 1
        else:
            parsed_tokens += char

    return parsed_tokens

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <filename>")
        exit(1)

    with open(sys.argv[1], "r") as f:
        tokens = femscript.make_tokens(f.read())

    result = femscript.parse_tokens(tokens, [])

    tokens = [Token(token["type"], token["value"]) for token in tokens]
    result = Token(result["type"], result["value"])

    print(code_from_tokens(tokens))
    print(parse_tokens(tokens))
    print("result 1 :", result)