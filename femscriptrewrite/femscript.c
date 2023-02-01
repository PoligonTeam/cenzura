// Copyright 2022 PoligonTeam

// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at

//     http://www.apache.org/licenses/LICENSE-2.0

// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <python3.11/Python.h>

enum TokenType {
    UNKNOWN,

    LEFT_CURLY_BRACKET,
    RIGHT_CURLY_BRACKET,
    LEFT_BRACKET,
    RIGHT_BRACKET,
    COMMA,
    DOT,
    COLON,
    PLUS,
    MINUS,
    MULTIPLY,
    DIVIDE,
    MODULO,
    ASSIGN,
    NOT,
    GREATER,
    LESS,
    COMMENT,
    NEWLINE,

    IF,
    ELSE,
    AND,
    OR,
    FUNC,
    IMPORT,
    RETURN,

    VAR,
    STR,
    INT,
    BOOL,
    LIST,
    DICT,

    ERROR,
    UNDEFINED,
    SYNTAX_ERROR,
    TYPE_ERROR
};

typedef struct {
    int type;
    char *value;
} Token;

typedef struct {
    char *name;
    int type;
    char *value;
} Variable;

typedef struct {
    char *name;
    char **args;
    char **kwargs[2];
    Token *tokens;
} Function;

Token *makeTokens(char *code) {
    Token *tokens = malloc(1024 * sizeof(Token));
    memset(tokens, 0, 1024 * sizeof(Token));

    int tokensCount = 0, position = 0;

    char currentChar;

    while (position < (int) strlen(code)) {
        currentChar = code[position];

        if (currentChar == '{') {
            tokens[tokensCount].type = LEFT_CURLY_BRACKET;
            tokens[tokensCount].value = "{";
            tokensCount++;
        } else if (currentChar == '}') {
            tokens[tokensCount].type = RIGHT_CURLY_BRACKET;
            tokens[tokensCount].value = "}";
            tokensCount++;
        } else if (currentChar == '(') {
            tokens[tokensCount].type = LEFT_BRACKET;
            tokens[tokensCount].value = "(";
            tokensCount++;
        } else if (currentChar == ')') {
            tokens[tokensCount].type = RIGHT_BRACKET;
            tokens[tokensCount].value = ")";
            tokensCount++;
        } else if (currentChar == ',') {
            tokens[tokensCount].type = COMMA;
            tokens[tokensCount].value = ",";
            tokensCount++;
        } else if (currentChar == '.') {
            tokens[tokensCount].type = DOT;
            tokens[tokensCount].value = ".";
            tokensCount++;
        } else if (currentChar == ':') {
            tokens[tokensCount].type = COLON;
            tokens[tokensCount].value = ":";
            tokensCount++;
        } else if (currentChar == '+') {
            tokens[tokensCount].type = PLUS;
            tokens[tokensCount].value = "+";
            tokensCount++;
        } else if (currentChar == '-') {
            tokens[tokensCount].type = MINUS;
            tokens[tokensCount].value = "-";
            tokensCount++;
        } else if (currentChar == '*') {
            tokens[tokensCount].type = MULTIPLY;
            tokens[tokensCount].value = "*";
            tokensCount++;
        } else if (currentChar == '/') {
            tokens[tokensCount].type = DIVIDE;
            tokens[tokensCount].value = "/";
            tokensCount++;
        } else if (currentChar == '%') {
            tokens[tokensCount].type = MODULO;
            tokens[tokensCount].value = "%";
            tokensCount++;
        } else if (currentChar == '=') {
            tokens[tokensCount].type = ASSIGN;
            tokens[tokensCount].value = "=";
            tokensCount++;
        } else if (currentChar == '!') {
            tokens[tokensCount].type = NOT;
            tokens[tokensCount].value = "!";
            tokensCount++;
        } else if (currentChar == '>') {
            tokens[tokensCount].type = GREATER;
            tokens[tokensCount].value = ">";
            tokensCount++;
        } else if (currentChar == '<') {
            tokens[tokensCount].type = LESS;
            tokens[tokensCount].value = "<";
            tokensCount++;
        } else if (currentChar == '#') {
            char *comment = malloc(1024 * sizeof(char));

            for (int index = 0; code[position] != '\n'; index++) {
                comment[index] = code[position];
                position++;
            }

            position--;

            tokens[tokensCount].type = COMMENT;
            tokens[tokensCount].value = comment;
            tokensCount++;
        } else if (currentChar == '\n') {
            tokens[tokensCount].type = NEWLINE;
            tokens[tokensCount].value = "\n";
            tokensCount++;
        } else if (currentChar >= '0' && currentChar <= '9') {
            char *number = malloc(20 * sizeof(char));
            memset(number, 0, 20 * sizeof(char));

            int numberCount = 0;

            while (currentChar >= '0' && currentChar <= '9') {
                number[numberCount] = currentChar;
                numberCount++;
                position++;
                currentChar = code[position];
            }

            tokens[tokensCount].type = INT;
            tokens[tokensCount].value = number;
            tokensCount++;
            continue;
        } else if (currentChar >= 'A' && currentChar <= 'z') {
            char *word = malloc(20 * sizeof(char));
            memset(word, 0, 20 * sizeof(char));

            int wordCount = 0;

            while (currentChar >= 'A' && currentChar <= 'z') {
                word[wordCount] = currentChar;
                wordCount++;
                position++;
                currentChar = code[position];
            }

            if (strcmp(word, "true") == 0) {
                tokens[tokensCount].type = BOOL;
                tokens[tokensCount].value = "true";
            } else if (strcmp(word, "false") == 0) {
                tokens[tokensCount].type = BOOL;
                tokens[tokensCount].value = "false";
            } else if (strcmp(word, "import") == 0) {
                tokens[tokensCount].type = IMPORT;
                tokens[tokensCount].value = word;
            } else if (strcmp(word, "return") == 0) {
                tokens[tokensCount].type = RETURN;
                tokens[tokensCount].value = word;
            } else if (strcmp(word, "if") == 0) {
                tokens[tokensCount].type = IF;
                tokens[tokensCount].value = word;
            } else if (strcmp(word, "else") == 0) {
                tokens[tokensCount].type = ELSE;
                tokens[tokensCount].value = word;
            } else if (strcmp(word, "and") == 0) {
                tokens[tokensCount].type = AND;
                tokens[tokensCount].value = word;
            } else if (strcmp(word, "or") == 0) {
                tokens[tokensCount].type = OR;
                tokens[tokensCount].value = word;
            } else if (strcmp(word, "func") == 0) {
                tokens[tokensCount].type = FUNC;
                tokens[tokensCount].value = word;
            } else {
                tokens[tokensCount].type = VAR;
                tokens[tokensCount].value = word;
            }

            tokensCount++;
            continue;
        } else if (currentChar == '"') {
            char *string = malloc(1024 * sizeof(char));
            memset(string, 0, 1024 * sizeof(char));

            int stringCount = 0;

            position++;
            currentChar = code[position];

            while (currentChar != '"') {
                string[stringCount] = currentChar;
                stringCount++;
                position++;
                currentChar = code[position];
            }

            tokens[tokensCount].type = STR;
            tokens[tokensCount].value = string;
            tokensCount++;
        }

        position++;
    }

    return tokens;
}

int getVariableIndex(Variable *variables, int variablesLength, Token *token) {
    for (int index = 0; index < variablesLength; index++)
        if (strcmp(variables[index].name, token->value) == 0)
            return index;

    return -1;
}

Token notDefined(Token *token) {
    char *message = malloc(100 * sizeof(char));
    sprintf(message, "Variable '%s' is not defined", token->value);

    return (Token) { UNDEFINED, message };
}

Token syntaxError(Token *previousToken, Token *token, Token *nextToken) {
    char *message = malloc(100 * sizeof(char));

    if (previousToken->type != 0 && nextToken->value != 0)
        sprintf(message, "Syntax error near '%s', '%s', and '%s'", previousToken->value, token->value, nextToken->value);
    else if (previousToken->type != 0)
        sprintf(message, "Syntax error near '%s', and '%s'", previousToken->value, token->value);
    else if (nextToken->type != 0)
        sprintf(message, "Syntax error near '%s', and '%s'", token->value, nextToken->value);
    else
        sprintf(message, "Syntax error near '%s'", token->value);

    return (Token) { SYNTAX_ERROR, message };
}

Token typeError(Token *previousToken, Token *token, Token *nextToken, char *expectedType) {
    char *message = malloc(100 * sizeof(char));

    if (previousToken->type != 0 && nextToken->value != 0)
        sprintf(message, "Type error near '%s', '%s', and '%s', expected '%s'", previousToken->value, token->value, nextToken->value, expectedType);
    else if (previousToken->type != 0)
        sprintf(message, "Type error near '%s', and '%s', expected '%s'", previousToken->value, token->value, expectedType);
    else if (nextToken->type != 0)
        sprintf(message, "Type error near '%s', and '%s', expected '%s'", token->value, nextToken->value, expectedType);
    else
        sprintf(message, "Type error near '%s', expected '%s'", token->value, expectedType);

    return (Token) { TYPE_ERROR, message };
}

Token parseTokens(Token *tokens, int length, Variable *variables, int variablesLength, Function *functions, int functionsLength) {
    int index = 0, oneLine = 1;

    Token unknown = (Token) { 0 };

    Token *currentToken = &unknown;
    Token *nextToken = &unknown;
    Token *previousToken = &unknown;

    for (int index = 0; index < length; index++)
        if (tokens[index].type == NEWLINE)
            oneLine = 0;

    while (index < length) {
        currentToken = &tokens[index];

        if (index + 1 < length)
            nextToken = &tokens[index + 1];
        else
            nextToken = &unknown;

        if (index - 1 >= 0)
            previousToken = &tokens[index - 1];
        else
            previousToken = &unknown;

        if (currentToken->type == ASSIGN && nextToken->type != ASSIGN) {
            if (previousToken->type == VAR) {
                if (index + 2 < length && tokens[index + 2].type != NEWLINE) {
                    index++;
                    continue;
                }

                char *nextValue = nextToken->value;

                if (nextToken->type < VAR || nextToken->type > DICT)
                    return syntaxError(previousToken, currentToken, nextToken);

                if (nextToken->type == VAR) {
                    int variableIndex = getVariableIndex(variables, variablesLength, nextToken);

                    if (variableIndex == -1)
                        return notDefined(nextToken);

                    nextValue = variables[variableIndex].value;
                }

                int variableIndex = getVariableIndex(variables, variablesLength, previousToken);

                if (variableIndex == -1)
                    variableIndex = variablesLength++;

                Variable *variable = &variables[variableIndex];

                variable->name = previousToken->value;
                variable->type = nextToken->type;
                variable->value = nextValue;
            }
        } else if (currentToken->type == COMMENT) {
            while (index < length && tokens[index].type != NEWLINE)
                index++;

            currentToken = &tokens[index];
            continue;
        } else if (currentToken->type >= PLUS && currentToken->type <= MODULO) {
            int previousValue = 0, nextValue = 0, result = 0;

            int assign = 0;

            if (nextToken->type == ASSIGN) {
                nextToken = &tokens[index + 2];
                assign = 1;
            }

            if (previousToken->type < VAR || previousToken->type > DICT)
                return syntaxError(previousToken, currentToken, nextToken);

            if (nextToken->type < VAR || nextToken->type > DICT)
                return syntaxError(previousToken, currentToken, nextToken);

            if (previousToken->type == VAR) {
                int variableIndex = getVariableIndex(variables, variablesLength, previousToken);

                if (variableIndex == -1)
                    return notDefined(previousToken);

                previousValue = atoi(variables[variableIndex].value);
            } else if (previousToken->type == INT) {
                previousValue = atoi(previousToken->value);
            } else {
                return typeError(previousToken, currentToken, nextToken, "int");
            }

            if (nextToken->type == VAR) {
                int variableIndex = getVariableIndex(variables, variablesLength, nextToken);

                if (variableIndex == -1)
                    return notDefined(nextToken);

                nextValue = atoi(variables[variableIndex].value);
            } else if (nextToken->type == INT) {
                nextValue = atoi(nextToken->value);
            } else {
                return typeError(previousToken, currentToken, nextToken, "int");
            }

            if (currentToken->type == PLUS)
                result = previousValue + nextValue;
            else if (currentToken->type == MINUS)
                result = previousValue - nextValue;
            else if (currentToken->type == MULTIPLY)
                result = previousValue * nextValue;
            else if (currentToken->type == DIVIDE)
                result = previousValue / nextValue;
            else if (currentToken->type == MODULO)
                result = previousValue % nextValue;

            char *resultString = malloc(20 * sizeof(char));
            memset(resultString, 0, 20 * sizeof(char));

            sprintf(resultString, "%d", result);

            if (assign) {
                int variableIndex = getVariableIndex(variables, variablesLength, previousToken);

                if (variableIndex == -1)
                    return notDefined(previousToken);

                Variable *variable = &variables[variableIndex];

                variable->value = resultString;

                index += 2;
                continue;
            }

            previousToken->type = INT;
            previousToken->value = resultString;

            currentToken->type = NEWLINE;
            currentToken->value = "\n";

            nextToken->type = NEWLINE;
            nextToken->value = "\n";

            if (oneLine)
                return *previousToken;

            index = 0;
            continue;
        } else if ((currentToken->type == ASSIGN || currentToken->type == NOT) && nextToken->type == ASSIGN) {
            nextToken = &tokens[index + 2];

            if (nextToken->type < VAR || nextToken->type > DICT)
                return syntaxError(previousToken, currentToken, nextToken);

            if (previousToken->type < VAR || previousToken->type > DICT)
                return syntaxError(previousToken, currentToken, nextToken);

            char *nextValue = nextToken->value;
            char *previousValue = previousToken->value;

            if (nextToken->type == VAR) {
                int variableIndex = getVariableIndex(variables, variablesLength, nextToken);

                if (variableIndex == -1)
                    return notDefined(nextToken);

                nextValue = variables[variableIndex].value;
            }

            if (previousToken->type == VAR) {
                int variableIndex = getVariableIndex(variables, variablesLength, previousToken);

                if (variableIndex == -1)
                    return notDefined(previousToken);

                previousValue = variables[variableIndex].value;
            }

            if (currentToken->type == ASSIGN) {
                if (strcmp(previousValue, nextValue) == 0) {
                    previousToken->type = BOOL;
                    previousToken->value = "true";
                } else {
                    previousToken->type = BOOL;
                    previousToken->value = "false";
                }
            } else if (currentToken->type == NOT) {
                if (strcmp(previousValue, nextValue) != 0) {
                    previousToken->type = BOOL;
                    previousToken->value = "true";
                } else {
                    previousToken->type = BOOL;
                    previousToken->value = "false";
                }
            }

            currentToken->type = NEWLINE;
            currentToken->value = "\n";

            nextToken->type = NEWLINE;
            nextToken->value = "\n";

            if (oneLine)
                return *previousToken;

            index = 0;
            continue;
        } else if (currentToken->type == GREATER || currentToken->type == LESS) {
            int previousValue = 0, nextValue = 0;

            int equal = 0;

            if (nextToken->type == ASSIGN) {
                nextToken = &tokens[index + 2];
                equal = 1;
            }

            if (previousToken->type < VAR || previousToken->type > DICT)
                return syntaxError(previousToken, currentToken, nextToken);

            if (nextToken->type < VAR || nextToken->type > DICT)
                return syntaxError(previousToken, currentToken, nextToken);

            if (previousToken->type == VAR) {
                int variableIndex = getVariableIndex(variables, variablesLength, previousToken);

                if (variableIndex == -1)
                    return notDefined(previousToken);

                if (variables[variableIndex].type != INT)
                    return typeError(previousToken, currentToken, nextToken, "int");

                previousValue = atoi(variables[variableIndex].value);
            } else if (previousToken->type == INT) {
                previousValue = atoi(previousToken->value);
            } else {
                return typeError(previousToken, currentToken, nextToken, "int");
            }

            if (nextToken->type == VAR) {
                int variableIndex = getVariableIndex(variables, variablesLength, nextToken);

                if (variableIndex == -1)
                    return notDefined(nextToken);

                if (variables[variableIndex].type != INT)
                    return typeError(previousToken, currentToken, nextToken, "int");

                nextValue = atoi(variables[variableIndex].value);
            } else if (nextToken->type == INT) {
                nextValue = atoi(nextToken->value);
            } else {
                return typeError(previousToken, currentToken, nextToken, "int");
            }

            if (currentToken->type == GREATER) {
                if (equal) {
                    if (previousValue >= nextValue) {
                        previousToken->type = BOOL;
                        previousToken->value = "true";
                    } else {
                        previousToken->type = BOOL;
                        previousToken->value = "false";
                    }
                } else {
                    if (previousValue > nextValue) {
                        previousToken->type = BOOL;
                        previousToken->value = "true";
                    } else {
                        previousToken->type = BOOL;
                        previousToken->value = "false";
                    }
                }
            } else if (currentToken->type == LESS) {
                if (equal) {
                    if (previousValue <= nextValue) {
                        previousToken->type = BOOL;
                        previousToken->value = "true";
                    } else {
                        previousToken->type = BOOL;
                        previousToken->value = "false";
                    }
                } else {
                    if (previousValue < nextValue) {
                        previousToken->type = BOOL;
                        previousToken->value = "true";
                    } else {
                        previousToken->type = BOOL;
                        previousToken->value = "false";
                    }
                }
            }

            currentToken->type = NEWLINE;
            currentToken->value = "\n";

            nextToken->type = NEWLINE;
            nextToken->value = "\n";

            if (oneLine)
                return *previousToken;

            index = 0;
            continue;
        } else if (currentToken->type == IF) {
            previousToken = currentToken;
            currentToken = nextToken;
            nextToken = &tokens[index + 2];

            int currentValue = 0, endIfIndex = 0;

            if (currentToken->type == LEFT_CURLY_BRACKET) {
                int endBlockIndex = 0;

                for (int _index = index; _index < length; _index++) {
                    if (tokens[_index].type == RIGHT_CURLY_BRACKET) {
                        endBlockIndex = _index;
                        break;
                    }
                }

                if (endBlockIndex == 0)
                    return syntaxError(previousToken, currentToken, nextToken);

                Token *block = malloc((endBlockIndex - index) * sizeof(Token));

                for (int _index = index + 2; _index < endBlockIndex; _index++) {
                    block[_index - index].type = tokens[_index].type;
                    block[_index - index].value = tokens[_index].value;
                }


                Token result = parseTokens(block, endBlockIndex - index, variables, variablesLength, functions, functionsLength);

                for (int _index = index + 1; _index < endBlockIndex + 1; _index++) {
                    tokens[_index].type = UNKNOWN;
                    tokens[_index].value = 0;
                }

                if (result.type >= ERROR && result.type <= TYPE_ERROR)
                    return result;

                currentToken->type = result.type;
                currentToken->value = result.value;

                nextToken->type = LEFT_CURLY_BRACKET;
                nextToken->value = "{";
            }

            if (currentToken->type < VAR || currentToken->type > DICT)
                return syntaxError(previousToken, currentToken, nextToken);

            if (currentToken->type == VAR) {
                int variableIndex = getVariableIndex(variables, variablesLength, currentToken);

                if (variableIndex == -1)
                    return notDefined(currentToken);

                if (variables[variableIndex].type != BOOL)
                    return typeError(previousToken, currentToken, nextToken, "bool");

                if (strcmp(variables[variableIndex].value, "true") == 0)
                    currentValue = 1;
                else if (strcmp(variables[variableIndex].value, "false") == 0)
                    currentValue = 0;
                else
                    return typeError(previousToken, currentToken, nextToken, "bool");
            } else if (currentToken->type == BOOL) {
                if (strcmp(currentToken->value, "true") == 0)
                    currentValue = 1;
                else if (strcmp(currentToken->value, "false") == 0)
                    currentValue = 0;
                else
                    return typeError(previousToken, currentToken, nextToken, "bool");
            } else {
                return typeError(previousToken, currentToken, nextToken, "bool");
            }

            if (nextToken->type != LEFT_CURLY_BRACKET)
                return syntaxError(previousToken, currentToken, nextToken);

            for (int _index = index; _index < length; _index++) {
                if (tokens[_index].type == RIGHT_CURLY_BRACKET) {
                    endIfIndex = _index;
                    break;
                }
            }

            if (endIfIndex == 0)
                return syntaxError(previousToken, currentToken, nextToken);

            if (currentValue) {
                previousToken->type = NEWLINE;
                previousToken->value = "\n";

                currentToken->type = NEWLINE;
                currentToken->value = "\n";

                nextToken->type = NEWLINE;
                nextToken->value = "\n";

                tokens[endIfIndex].type = NEWLINE;
                tokens[endIfIndex].value = "\n";
            } else {
                for (int _index = index; _index < endIfIndex; _index++) {
                    tokens[_index].type = NEWLINE;
                    tokens[_index].value = "\n";
                }
            }

            index = 0;
            continue;
        } else if (currentToken->type == AND || currentToken->type == OR) {
            int previousValue = 0, nextValue = 0;

            if (previousToken->type < VAR || previousToken->type > DICT)
                return syntaxError(previousToken, currentToken, nextToken);

            if (nextToken->type < VAR || nextToken->type > DICT)
                return syntaxError(previousToken, currentToken, nextToken);

            if (previousToken->type == VAR) {
                int variableIndex = getVariableIndex(variables, variablesLength, previousToken);

                if (variableIndex == -1)
                    return notDefined(previousToken);

                if (strcmp(variables[variableIndex].value, "true") == 0)
                    previousValue = 1;
                else if (strcmp(variables[variableIndex].value, "false") == 0)
                    previousValue = 0;
                else
                    return typeError(previousToken, currentToken, nextToken, "bool");
            } else if (previousToken->type == BOOL) {
                if (strcmp(previousToken->value, "true") == 0)
                    previousValue = 1;
                else if (strcmp(previousToken->value, "false") == 0)
                    previousValue = 0;
                else
                    return typeError(previousToken, currentToken, nextToken, "bool");
            } else {
                return typeError(previousToken, currentToken, nextToken, "bool");
            }

            if (nextToken->type == VAR) {
                int variableIndex = getVariableIndex(variables, variablesLength, nextToken);

                if (variableIndex == -1)
                    return notDefined(nextToken);

                if (strcmp(variables[variableIndex].value, "true") == 0)
                    nextValue = 1;
                else if (strcmp(variables[variableIndex].value, "false") == 0)
                    nextValue = 0;
                else
                    return typeError(previousToken, currentToken, nextToken, "bool");
            } else if (nextToken->type == BOOL) {
                if (strcmp(nextToken->value, "true") == 0)
                    nextValue = 1;
                else if (strcmp(nextToken->value, "false") == 0)
                    nextValue = 0;
                else
                    return typeError(previousToken, currentToken, nextToken, "bool");
            } else {
                return typeError(previousToken, currentToken, nextToken, "bool");
            }

            if (currentToken->type == AND) {
                if (previousValue && nextValue) {
                    previousToken->type = BOOL;
                    previousToken->value = "true";
                } else {
                    previousToken->type = BOOL;
                    previousToken->value = "false";
                }
            } else if (currentToken->type == OR) {
                if (previousValue || nextValue) {
                    previousToken->type = BOOL;
                    previousToken->value = "true";
                } else {
                    previousToken->type = BOOL;
                    previousToken->value = "false";
                }
            }

            currentToken->type = NEWLINE;
            currentToken->value = "\n";

            nextToken->type = NEWLINE;
            nextToken->value = "\n";

            if (oneLine)
                return *previousToken;

            index = 0;
            continue;
        } else if (currentToken-> type == NOT) {
            int nextValue = 0;

            if (nextToken->type < VAR || nextToken->type > DICT)
                return syntaxError(previousToken, currentToken, nextToken);

            if (nextToken->type == VAR) {
                int variableIndex = getVariableIndex(variables, variablesLength, nextToken);

                if (variableIndex == -1)
                    return notDefined(nextToken);

                if (strcmp(variables[variableIndex].value, "true") == 0)
                    nextValue = 1;
                else if (strcmp(variables[variableIndex].value, "false") == 0)
                    nextValue = 0;
                else
                    return typeError(previousToken, currentToken, nextToken, "bool");
            } else if (nextToken->type == BOOL) {
                if (strcmp(nextToken->value, "true") == 0)
                    nextValue = 1;
                else if (strcmp(nextToken->value, "false") == 0)
                    nextValue = 0;
                else
                    return typeError(previousToken, currentToken, nextToken, "bool");
            } else {
                return typeError(previousToken, currentToken, nextToken, "bool");
            }

            if (nextValue) {
                currentToken->type = BOOL;
                currentToken->value = "false";
            } else {
                currentToken->type = BOOL;
                currentToken->value = "true";
            }

            nextToken->type = NEWLINE;
            nextToken->value = "\n";

            if (oneLine)
                return *currentToken;

            index = 0;
            continue;
        } else if (currentToken->type == FUNC) {

        } else if (currentToken->type == IMPORT) {
            return (Token) { ERROR, "import is not implemented yet" };
        } else if (currentToken->type == RETURN) {
            if (nextToken->type < VAR || nextToken->type > DICT)
                return syntaxError(previousToken, currentToken, nextToken);

            if (nextToken->type == VAR) {
                int variableIndex = getVariableIndex(variables, variablesLength, nextToken);

                if (variableIndex == -1)
                    return notDefined(nextToken);

                Variable *variable = &variables[variableIndex];

                return (Token) { variable->type, variable->value };
            }

            return *nextToken;
        }

        index++;
    }

    if (oneLine && currentToken->type >= STR && currentToken->type <= DICT)
        return *currentToken;

    return unknown;
}

static PyObject *make_tokens(PyObject *self, PyObject *args) {
    char *code;

    if (!PyArg_ParseTuple(args, "s", &code))
        return NULL;

    Token *tokens = makeTokens(code);

    PyObject *list = PyList_New(0);

    for (int index = 0; index < 1024; index++) {
        if (tokens[index].type != 0) {
            PyObject *token = Py_BuildValue("{s:i,s:s}", "type", tokens[index].type, "value", tokens[index].value);
            PyList_Append(list, token);
        }
    }

    return list;
}

static PyObject *parse_tokens(PyObject *self, PyObject *args) {
    PyObject *tokens;
    PyObject *variables;

    if (!PyArg_ParseTuple(args, "OO", &tokens, &variables))
        return NULL;

    Token *tokensArray = malloc(1024 * sizeof(Token));
    int length = 0;

    for (int index = 0; index < 1024; index++) {
        if (PyList_Size(tokens) > index) {
            PyObject *token = PyList_GetItem(tokens, index);
            PyObject *type = PyDict_GetItemString(token, "type");
            PyObject *value = PyDict_GetItemString(token, "value");

            tokensArray[index].type = PyLong_AsLong(type);
            tokensArray[index].value = (char *)PyUnicode_AsUTF8(value);

            length++;
        }
    }

    Variable *variablesArray = malloc(1024 * sizeof(Variable));
    int variablesLength = 0;

    for (int index = 0; index < 1024; index++) {
        if (PyList_Size(variables) > index) {
            PyObject *variable = PyList_GetItem(variables, index);
            PyObject *name = PyDict_GetItemString(variable, "name");
            PyObject *type = PyDict_GetItemString(variable, "type");
            PyObject *value = PyDict_GetItemString(variable, "value");

            variablesArray[index].name = (char *)PyUnicode_AsUTF8(name);
            variablesArray[index].type = PyLong_AsLong(type);
            variablesArray[index].value = (char *)PyUnicode_AsUTF8(value);

            variablesLength++;
        }
    }

    Function *functions = malloc(1024 * sizeof(Function));
    int functionsLength = 0;

    Token result = parseTokens(tokensArray, length, variablesArray, variablesLength, functions, functionsLength);

    PyObject *token = Py_BuildValue("{s:i,s:s}", "type", result.type, "value", result.value);

    return token;
}

static PyMethodDef FemscriptMethods[] = {
    {"make_tokens", make_tokens, METH_VARARGS, NULL},
    {"parse_tokens", parse_tokens, METH_VARARGS, NULL}
};

static struct PyModuleDef FemscriptModule = {
    PyModuleDef_HEAD_INIT,
    "femscript",
    NULL,
    -1,
    FemscriptMethods
};

PyMODINIT_FUNC PyInit_femscript() {
    return PyModule_Create(&FemscriptModule);
}