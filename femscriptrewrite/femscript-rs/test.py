import operator

def parse(inp):
    out = []
    stack = []

    precedence = {
        "+": 1,
        "-": 1,
        "*": 2,
        "/": 2,
        "%": 2
    }

    skip = 0

    for index, token in enumerate(inp):
        if skip > index:
            continue

        if token == "(":
            tokens = []
            count = 1

            for token in inp[index+1:]:
                if token == "(":
                    count += 1
                elif token == ")":
                    count -= 1

                if count == 0:
                    break

                tokens.append(token)
            else:
                raise Exception("Syntax error: ( is not closed")

            skip = index + len(tokens) + 1

            out.extend(parse(tokens))
        elif token in precedence:
            if not stack:
                stack.append(token)
            else:
                if precedence[token] > precedence[stack[0]]:
                    stack.insert(0, token)
                else:
                    out.append(stack.pop(0))
                    stack.append(token)
        elif token.isdigit():
            out.append(token)

    out.extend(stack)

    return out

def main():
    inp = "2 * ( 2 + 2 )".split(" ")
    equation = parse(inp)

    stack = []

    operators = {
        "+": operator.add,
        "-": operator.sub,
        "*": operator.mul,
        "/": operator.truediv,
        "%": operator.mod
    }

    for token in equation:
        if token.isdigit():
            stack.append(int(token))
        elif token in operators:
            stack.append(operators[token](stack.pop(-2), stack.pop()))
        else:
            stack.append(token)

    print("".join(inp), "=", "".join([("(" + x + ")") if x.isdigit() else x for x in equation]), "=", stack[0])

def parse2(inp):
    out = []
    stack = []
    opstack = []

    precedence = {
        "+": 1,
        "-": 1,
        "*": 2,
        "/": 2,
        "%": 2
    }

    skip = 0

    for index, token in enumerate(inp):
        if skip > index:
            continue

        if token == "(":
            tokens = []
            count = 1

            for token in inp[index+1:]:
                if token == "(":
                    count += 1
                elif token == ")":
                    count -= 1

                if count == 0:
                    break

                tokens.append(token)
            else:
                raise Exception("Syntax error: ( is not closed")

            skip = index + len(tokens) + 1

            out.extend(parse(tokens))
        elif token.isdigit():
            if not out:
                out.append(token)
            elif opstack:
                out.append(token)
            else:
                stack.append(token)
        elif token in precedence:
            if not opstack:
                opstack.append(token)
            else:
                if precedence[token] > precedence[opstack[-1]]:
                    out.append(opstack.pop())
                    out.append(stack.pop())
                else:
                    out.append(token)

    return out

def main2():
    inp = "2 * ( 2 + 2 )".split(" ")
    equation = parse2(inp)

    print(equation)

if __name__ == "__main__":
    main2()