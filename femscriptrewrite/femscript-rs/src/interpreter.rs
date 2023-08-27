/*
Copyright 2022 czubix

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

use crate::lexer::{Token, TokenType, generate_tokens};
use crate::parser::{AST, ASTType, generate_ast};
use crate::builtins::get_builtins;
use crate::utils::*;
use pyo3::{prelude::*, types::PyTuple};

#[derive(Clone, Debug)]
pub struct Variable {
    pub name: String,
    pub value: Token,
    pub scope: Option<Scope>
}

#[derive(Clone, Debug)]
pub struct Function {
    pub name: String,
    pub args: Vec<String>,
    pub body: Option<Vec<AST>>,
    pub func: Option<fn (String, Vec<Token>, Scope) -> Token>
}

impl Function {
    pub fn new_builtin(name: &str, function: fn (String, Vec<Token>, Scope) -> Token) -> Self {
        Self {
            name: name.to_string(),
            args: Vec::new(),
            body: None,
            func: Some(function)
        }
    }
}

#[derive(Clone, Debug)]
pub struct Scope {
    pub variables: Vec<Variable>,
    pub functions: Vec<Function>
}

#[allow(dead_code)]
impl Scope {
    pub fn new() -> Self {
        Self {
            variables: Vec::new(),
            functions: Vec::new()
        }
    }

    pub fn push_variable(&mut self, name: &str, value: Token, scope: Option<Scope>) {
        self.variables.push(Variable {
            name: name.to_string(),
            value,
            scope
        });
    }

    pub fn push_function(&mut self, name: &str, function: fn(String, Vec<Token>, Scope) -> Token) {
        self.functions.push(Function {
            name: name.to_string(),
            args: Vec::new(),
            body: None,
            func: Some(function)
        });
    }
}

pub fn get_variable<'a>(name: &'a str, scope: &'a mut Scope) -> Option<&'a mut Variable> {
    for variable in &mut scope.variables {
        if variable.name == name {
            return Some(variable);
        }
    }

    None
}

pub fn get_function<'a>(name: &'a str, scope: &'a mut Scope) -> Option<&'a Function> {
    for function in &scope.functions {
        if function.name == name {
            return Some(function);
        }
    }

    None
}

fn check_if_error(token: &Token) -> bool {
    token._type == TokenType::Error ||
    token._type == TokenType::Undefined ||
    token._type == TokenType::RecursionError ||
    token._type == TokenType::SyntaxError ||
    token._type == TokenType::TypeError
}

pub fn execute_ast(ast: Vec<AST>, scope: &mut Scope, context: Option<Token>, depth: u32) -> Token {
    let mut result = Token::new(TokenType::Unknown);
    let mut context = context.unwrap_or(Token::new(TokenType::Unknown));

    if depth > 100 {
        return Token::new_error(TokenType::RecursionError, "Maximum recursion depth exceeded".to_string());
    }

    for node in ast {
        match node._type {
            ASTType::Error => {
                return node.token;
            },
            ASTType::Block => {
                if context._type != TokenType::Unknown {
                    let mut block_scope = Scope::new();

                    if let Some(borrow_ast) = &node.children.get(0) {
                        if borrow_ast.token.value == "borrow" {
                            for ast_token in &borrow_ast.children.get(0).unwrap().children {
                                if let Some(variable) = get_variable(&ast_token.token.value, scope) {
                                    block_scope.variables.push(variable.to_owned());
                                } else {
                                    return Token::new_error(TokenType::TypeError, format!("{} is not defined", ast_token.token.value));
                                }
                            }
                        }
                    }

                    result = execute_ast(node.children, &mut block_scope, None, depth);

                    if check_if_error(&result) {
                        return result;
                    }

                    if let Some(variable) = get_variable(&context.value, scope) {
                        variable.scope = Some(block_scope);
                    } else {
                        scope.variables.push(Variable {
                            name: context.value.to_owned(),
                            value: result,
                            scope: Some(block_scope)
                        });
                    }

                    result = Token::new(TokenType::Scope);
                } else {
                    result = execute_ast(node.children, scope, Some(node.token.to_owned()), depth);

                    if check_if_error(&result) {
                        return result;
                    }
                }
            },
            ASTType::Token => {
                match node.token._type {
                    TokenType::Error |
                    TokenType::Undefined |
                    TokenType::SyntaxError |
                    TokenType::TypeError => {
                        return node.token;
                    },
                    TokenType::Int |
                    TokenType::Str |
                    TokenType::Bool |
                    TokenType::None => {
                        if node.children.is_empty() {
                            result = node.token;
                        } else {
                            result = execute_ast(node.children, scope, Some(node.token.to_owned()), depth);

                            if check_if_error(&result) {
                                return result;
                            }
                        }
                    },
                    TokenType::List => {
                        if node.children.is_empty() {
                            result = node.token;
                        } else {
                            for child in node.children {
                                let child_result = execute_ast(vec![child], scope, None, depth);

                                if check_if_error(&child_result) {
                                    return child_result;
                                }

                                result._type = TokenType::List;
                                result.list.push(child_result);
                            }
                        }
                    },
                    TokenType::Var => {
                        if context._type != TokenType::Unknown {
                            if let Some(variable) = get_variable(&context.value, scope) {
                                if let Some(context_scope) = &variable.scope {
                                    if let Some(variable_variable) = get_variable(&node.token.value, &mut context_scope.to_owned()) {
                                        if node.children.is_empty() {
                                            return variable_variable.value.to_owned();
                                        } else {
                                            return execute_ast(node.children, &mut context_scope.to_owned(), Some(node.token.to_owned()), depth);
                                        }
                                    } else {
                                        return Token::new_error(TokenType::TypeError, format!("{} is not defined", node.token.value));
                                    }
                                } else {
                                    if variable.value._type == TokenType::PyObject {
                                        let variable = variable.to_owned();

                                        result = execute_ast(node.children, scope, None, depth);

                                        if check_if_error(&result) {
                                            return result;
                                        }

                                        return Python::with_gil(|py| {
                                            let pyobject = variable.value.pyobject.to_object(py);
                                            let method_name = node.token.value.as_str();

                                            if method_name.starts_with("__") && method_name.ends_with("__") {
                                                return Token::new_error(TokenType::Error, format!("The '{}' attribute is not safe", method_name));
                                            }

                                            let py_args = PyTuple::new(py, result.list.iter().map(|arg| to_pyobject(py, arg.to_owned())));

                                            let py_result = pyobject.call_method1(py, method_name, py_args);

                                            if let Err(error) = py_result {
                                                return Token::new_error(TokenType::Error, format!("{}", error.value(py)));
                                            }

                                            to_token(py, py_result.unwrap())
                                        });
                                    } else {
                                        return Token::new_error(TokenType::TypeError, format!("{} is not defined", context.value));
                                    }
                                }
                            }
                        }

                        if let Some(variable) = get_variable(&node.token.value, scope) {
                            result = variable.value.to_owned();

                            if !node.children.is_empty() {
                                let mut _context = node.token.to_owned();

                                if node.children[0].token._type == TokenType::Dot {
                                    result = execute_ast(node.children, scope, Some(node.token.to_owned()), depth);

                                    if check_if_error(&result) {
                                        return result;
                                    }

                                    continue
                                }

                                result = execute_ast(node.children, scope, Some(_context), depth);

                                if check_if_error(&result) {
                                    return result;
                                }
                            }
                        } else if let Some(function) = get_function(&node.token.value, &mut scope.to_owned()) {
                            let args = execute_ast(node.children, scope, Some(node.token.to_owned()), depth);

                            if check_if_error(&args) {
                                return args;
                            }

                            let args = args.list;

                            if let Some(body) = &function.body {
                                if args.len() != function.args.len() {
                                    return Token::new_error(TokenType::TypeError, format!("{}() takes {} arguments", function.name, function.args.len()));
                                }

                                let mut function_scope = Scope {
                                    variables: scope.variables.to_owned(),
                                    functions: scope.functions.to_owned()
                                };

                                for (i, arg) in args.iter().enumerate() {
                                    function_scope.variables.push(Variable {
                                        name: function.args[i].to_owned(),
                                        value: arg.to_owned(),
                                        scope: None
                                    });
                                }

                                result = execute_ast(body.to_owned(), &mut function_scope, None, depth + 1);

                                if check_if_error(&result) {
                                    return result;
                                }

                                for function_variable in function_scope.variables {
                                    if !function.args.contains(&function_variable.name) {
                                        if let Some(variable) = get_variable(&function_variable.name, scope) {
                                            variable.value = function_variable.value;
                                        } else {
                                            scope.variables.push(function_variable);
                                        }
                                    }
                                }
                            } else if let Some(builtin) = function.func {
                                result = builtin(function.name.to_owned(), args, scope.to_owned());

                                if check_if_error(&result) {
                                    return result;
                                }
                            }
                        } else {
                            if node.children.is_empty() {
                                return Token::new_error(TokenType::Undefined, format!("Variable '{}' is not defined", node.token.value));
                            }

                            result = execute_ast(node.children, scope, Some(node.token.to_owned()), depth);

                            if check_if_error(&result) {
                                return result;
                            }
                        }
                    },
                    TokenType::Dot => {
                        result = execute_ast(node.children, scope, Some(context.to_owned()), depth);

                        if check_if_error(&result) {
                            return result;
                        }
                    },
                    _ => {
                        result = node.token;
                    }
                }
            },
            ASTType::Assign => {
                let context = context.to_owned();

                let value = execute_ast(node.children, scope, Some(context.to_owned()), depth);

                if check_if_error(&value) {
                    return value;
                }

                if let Some(variable) = get_variable(&context.value, scope) {
                    macro_rules! cumcat {
                        ($op:tt) => {
                            {
                                if (variable.value._type != value._type) && (variable.value._type != TokenType::List) {
                                    return Token::new_error(TokenType::TypeError, format!("Cannot assign {:?} to {:?}", value._type, variable.value._type));
                                }

                                match variable.value._type {
                                    TokenType::Int => variable.value.number $op value.number,
                                    TokenType::Str => match stringify!($op) {
                                        "+=" => variable.value.value.push_str(&value.value),
                                        _ => return Token::new_error(TokenType::TypeError, format!("Cannot assign {:?} to {:?}", value._type, variable.value._type))
                                    },
                                    TokenType::List => match stringify!($op) {
                                        "+=" => variable.value.list.push(value),
                                        _ => return Token::new_error(TokenType::TypeError, format!("Cannot assign {:?} to {:?}", value._type, variable.value._type))
                                    },
                                    _ => return Token::new_error(TokenType::TypeError, format!("Cannot assign {:?} to {:?}", value._type, variable.value._type))
                                }
                            }
                        };
                    }

                    match node.token._type {
                        TokenType::Equal => variable.value = value.to_owned(),
                        TokenType::PlusEqual => cumcat!(+=),
                        TokenType::MinusEqual => cumcat!(-=),
                        TokenType::MultiplyEqual => cumcat!(*=),
                        TokenType::DivideEqual => cumcat!(/=),
                        TokenType::ModuloEqual => cumcat!(%=),
                        _ => return Token::new_error(TokenType::TypeError, format!("Cannot assign {:?} to {:?}", value._type, variable.value._type))
                    }
                } else {
                    if result._type == TokenType::Scope {
                        continue;
                    }

                    scope.variables.push(Variable {
                        name: context.value,
                        value: value.to_owned(),
                        scope: None
                    });
                }
            },
            ASTType::Expression => {
                if let Some(variable) = get_variable(&context.value, scope) {
                    context = variable.value.to_owned();
                } else if context._type == TokenType::Var {
                    return Token::new_error(TokenType::SyntaxError, "Cannot assign to variable outside of scope".to_string());
                }

                let mut _result = Token::new_int(context.number);

                let children_result = execute_ast(node.children, scope, Some(_result.to_owned()), depth);

                if check_if_error(&children_result) {
                    return children_result;
                }

                macro_rules! cumpare {
                    ($op:tt) => {
                        {
                            if context._type != children_result._type {
                                return Token::new_error(TokenType::TypeError, "Cannot compare types".to_string());
                            }

                            match context._type {
                                TokenType::Int | TokenType::Bool => _result.number = if context.number $op children_result.number { 1.0 } else { 0.0 },
                                TokenType::Str => _result.number = if context.value $op children_result.value { 1.0 } else { 0.0 },
                                _ => return Token::new_error(TokenType::TypeError, "Cannot compare types".to_string())
                            }

                            _result = Token::new_bool(if _result.number == 0.0 { "false" } else { "true" }.to_string());
                        }
                    };
                }

                match node.token._type {
                    TokenType::Plus => _result.number += children_result.number,
                    TokenType::Minus => _result.number -= children_result.number,
                    TokenType::Multiply => _result.number *= children_result.number,
                    TokenType::Divide => _result.number /= children_result.number,
                    TokenType::Modulo => _result.number %= children_result.number,
                    TokenType::EqualTo => cumpare!(==),
                    TokenType::NotEqual => cumpare!(!=),
                    TokenType::Not => match children_result._type {
                        TokenType::Int | TokenType::Bool => {
                            _result.number = if children_result.number == 0.0 { 1.0 } else { 0.0 };
                            _result = Token::new_bool(if _result.number == 0.0 { "false" } else { "true" }.to_string());
                        },
                        TokenType::Str => {
                            _result.number = if children_result.value == "" { 1.0 } else { 0.0 };
                            _result = Token::new_bool(if _result.number == 0.0 { "false" } else { "true" }.to_string());
                        },
                        _ => return Token::new_error(TokenType::TypeError, "Cannot compare types".to_string())
                    },
                    TokenType::Greater => cumpare!(>),
                    TokenType::Less => cumpare!(<),
                    TokenType::GreaterEqual => cumpare!(>=),
                    TokenType::LessEqual => cumpare!(<=),
                    TokenType::And => _result.number = if context.number != 0.0 && children_result.number != 0.0 { 1.0 } else { 0.0 },
                    TokenType::Or => _result.number = if context.number != 0.0 || children_result.number != 0.0 { 1.0 } else { 0.0 },
                    _ => _result = Token::new_error(TokenType::SyntaxError, "Unknown operator".to_string())
                }

                if check_if_error(&_result) {
                    return _result;
                }

                result = _result;
            },
            ASTType::Keyword => {
                match node.token._type {
                    TokenType::If => {
                        let condition = execute_ast(node.children[0].children.to_owned(), scope, None, depth);

                        if check_if_error(&condition) {
                            return condition;
                        }

                        if condition.number == 1.0 {
                            result = execute_ast(node.children[1].children.to_owned(), scope, None, depth);
                        } else if node.children.len() == 3 {
                            result = execute_ast(node.children[2].children.to_owned(), scope, None, depth);
                        }

                        if check_if_error(&result) {
                            return result;
                        }
                    },
                    TokenType::Func => {
                        if node.children.len() != 3 {
                            return Token::new_error(TokenType::SyntaxError, "Invalid function definition".to_string());
                        }

                        scope.functions.push(Function {
                            name: node.children[0].token.value.to_owned(),
                            args: node.children[1].children.iter().map(|x| x.token.value.to_owned()).collect(),
                            body: Some(node.children[2].children.to_owned()),
                            func: None
                        });
                    },
                    TokenType::Return => {
                        result = execute_ast(node.children, scope, None, depth);

                        if check_if_error(&result) {
                            return result;
                        }

                        break;
                    },
                    _ => {}
                }
            }
        }
    }

    result
}

#[allow(dead_code)]
pub fn run(code: &str, scope: &mut Scope) -> Token {
    let mut builtins = get_builtins();

    scope.functions.append(&mut builtins);

    let tokens = generate_tokens(code);
    let ast = generate_ast(tokens.iter().collect());

    let result = execute_ast(ast, scope, None, 0);

    if result._type == TokenType::Unknown {
        return Token::new_none();
    }

    result
}