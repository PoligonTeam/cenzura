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

use crate::lexer::{Token, TokenType};
use crate::parser::{AST, ASTType};
use crate::utils::*;
use crate::builtins::call_builtin;
use pyo3::{prelude::*, types::{PyTuple, PyDict}};
use async_recursion::async_recursion;

#[derive(Clone, Debug)]
pub struct Variable {
    pub name: String,
    pub value: Token
}

#[derive(Clone, Debug)]
pub struct Function {
    pub name: String,
    pub args: Vec<String>,
    pub body: Option<Vec<AST>>,
    pub builtin: bool,
    pub pyfunc: Option<Py<PyAny>>
}

impl Function {
    pub fn new_builtin(name: &str) -> Self {
        Self {
            name: name.to_string(),
            args: Vec::new(),
            body: None,
            builtin: true,
            pyfunc: None
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

    pub fn push_variable(&mut self, name: &str, value: Token) {
        self.variables.push(Variable {
            name: name.to_string(),
            value
        });
    }

    pub fn push_builtin(&mut self, name: &str) {
        self.functions.push(Function {
            name: name.to_string(),
            args: Vec::new(),
            body: None,
            builtin: true,
            pyfunc: None
        });
    }

    pub fn push_pyfunc(&mut self, name: &str, pyfunc: Py<PyAny>) {
        self.functions.push(Function {
            name: name.to_string(),
            args: Vec::new(),
            body: None,
            builtin: false,
            pyfunc: Some(pyfunc)
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

#[async_recursion]
pub async fn execute_ast(ast: Vec<AST>, scope: &mut Scope, context: Option<Token>, depth: u32) -> Token {
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
                if let TokenType::Func | TokenType::If = context._type {
                    result = execute_ast(node.children, scope, Some(node.token.to_owned()), depth).await;

                    if check_if_error(&result) {
                        return result;
                    }
                } else {
                    let mut borrowed_scope = Scope::new();
                    let mut start = 0;

                    if let Some(borrow_ast) = &node.children.get(0) {
                        if borrow_ast.token.value == "borrow" {
                            start = 1;

                            for ast_token in &borrow_ast.children.get(0).unwrap().children {
                                if let Some(variable) = get_variable(&ast_token.token.value, scope) {
                                    borrowed_scope.variables.push(variable.to_owned());
                                } else {
                                    return Token::new_error(TokenType::Undefined, format!("{} is not defined", ast_token.token.value));
                                }
                            }
                        }
                    }

                    let mut block_scope = Scope::new();

                    block_scope.push_variable("&", Token::new_scope(borrowed_scope));

                    for function in &scope.functions {
                        if function.builtin == true {
                            block_scope.push_builtin(&function.name);
                        }
                    }

                    result = execute_ast(node.children[start..node.children.len()].to_vec(), &mut block_scope, None, depth).await;

                    if check_if_error(&result) {
                        return result;
                    }

                    let index = block_scope.variables.iter().position(|variable| variable.name == "&").unwrap();
                    block_scope.variables.remove(index);

                    result = Token::new_scope(block_scope);

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
                        result = if context._type == TokenType::Var && node.token._type == TokenType::Int {
                            result = if let Some(variable) = get_variable(&context.value, scope) {
                                if variable.value._type == TokenType::List {
                                    let len = variable.value.list.len();
                                    let mut num = node.token.number as i32;
                                    if num < 0 {
                                        num += len as i32;
                                    }
                                    if num as usize >= len {
                                        return Token::new_error(TokenType::IndexError, "list index out of range".to_string());
                                    }
                                    variable.value.list[num as usize].to_owned()
                                } else {
                                    node.token
                                }
                            } else {
                                node.token
                            };

                            if check_if_error(&result) {
                                return result;
                            }

                            if node.children.is_empty() {
                                result
                            } else {
                                execute_ast(node.children, scope, Some(result), depth).await
                            }
                        } else {
                            if node.children.is_empty() {
                                node.token
                            } else {
                                execute_ast(node.children, scope, Some(node.token.to_owned()), depth).await
                            }
                        };

                        if check_if_error(&result) {
                            return result;
                        }
                    },
                    TokenType::List => {
                        if node.children.is_empty() {
                            result = node.token;
                        } else {
                            for child in node.children {
                                let child_result = execute_ast(vec![child], scope, Some(node.token.to_owned()), depth).await;

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
                                if variable.value._type == TokenType::PyObject {
                                    let variable = variable.to_owned();

                                    let args_result = execute_ast(node.children, scope, Some(node.token.to_owned()), depth).await;

                                    if check_if_error(&args_result) {
                                        return args_result;
                                    }

                                    let args = args_result.list.to_owned();

                                    if check_if_error(&result) {
                                        return result;
                                    }

                                    return Python::with_gil(|py| {
                                        let pyobject = variable.value.pyobject.to_object(py);
                                        let method_name = node.token.value.as_str();

                                        if pyobject.getattr(py, "__class__").unwrap().getattr(py, "__name__").unwrap().extract::<String>(py).unwrap() == "coroutine" {
                                            return Token::new_error(TokenType::Error, format!("'{}' attribute is not safe", method_name));
                                        }

                                        if method_name.starts_with("__") && method_name.ends_with("__") {
                                            return Token::new_error(TokenType::Error, format!("'{}' attribute is not safe", method_name));
                                        }

                                        let py_result = match args_result._type {
                                            TokenType::List => {
                                                let py_args = PyTuple::new(py, args.iter().map(|arg| to_pyobject(py, arg.to_owned())));
                                                pyobject.call_method1(py, method_name, py_args)
                                            },
                                            TokenType::Scope => {
                                                let py_args = scope_to_pydict(py, args_result.scope.unwrap());
                                                pyobject.call_method(py, method_name, (), Some(py_args))
                                            },
                                            _ => return Token::new_error(TokenType::SyntaxError, "Function payload must be list or scope".to_string())
                                        };

                                        if let Err(error) = py_result {
                                            return Token::new_error(TokenType::Error, format!("{}", error.value(py)));
                                        }

                                        to_token(py, py_result.unwrap())
                                    });
                                } else if variable.value._type == TokenType::Scope {
                                    if let Some(token_scope) = &variable.value.scope {
                                        if let Some(variable_variable) = get_variable(&node.token.value, &mut token_scope.to_owned()) {
                                            if node.children.is_empty() {
                                                return variable_variable.value.to_owned();
                                            } else {
                                                return execute_ast(node.children, &mut token_scope.to_owned(), Some(node.token.to_owned()), depth).await;
                                            }
                                        } else {
                                            return Token::new_error(TokenType::Undefined, format!("{} is not defined", node.token.value));
                                        }
                                    } else {
                                        return Token::new_error(TokenType::Undefined, format!("{} is not defined", node.token.value));
                                    }
                                } else {
                                    return Token::new_error(TokenType::Undefined, format!("{} is not defined", context.value));
                                }
                            } else if context._type == TokenType::Scope {
                                result = if let Some(variable) = get_variable(&node.token.value, &mut context.scope.to_owned().unwrap()) {
                                    variable.value.to_owned()
                                } else {
                                    return Token::new_error(TokenType::Undefined, format!("{} is not defined", node.token.value))
                                };

                                return if node.children.is_empty() {
                                    result
                                } else {
                                    execute_ast(node.children, scope, Some(result), depth).await
                                }
                            }
                        }

                        if let Some(variable) = get_variable(&node.token.value, scope) {
                            result = variable.value.to_owned();

                            if !node.children.is_empty() {
                                let mut _context = node.token.to_owned();

                                if node.children[0].token._type == TokenType::Dot {
                                    result = execute_ast(node.children, scope, Some(node.token.to_owned()), depth).await;

                                    if check_if_error(&result) {
                                        return result;
                                    }

                                    continue
                                }

                                result = execute_ast(node.children, scope, Some(_context), depth).await;

                                if check_if_error(&result) {
                                    return result;
                                }
                            }
                        } else if let Some(function) = get_function(&node.token.value, &mut scope.to_owned()) {
                            let args_result = execute_ast(node.children, scope, Some(node.token.to_owned()), depth).await;

                            if check_if_error(&args_result) {
                                return args_result;
                            }

                            let args = args_result.list.to_owned();

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
                                        value: arg.to_owned()
                                    });
                                }

                                result = execute_ast(body.to_owned(), &mut function_scope, Some(Token::new(TokenType::Func)), depth + 1).await;

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
                            } else if let Some(pyfunc) = &function.pyfunc {
                                result = Python::with_gil(|py| {
                                    let py_result = match args_result._type {
                                        TokenType::List => {
                                            let py_args = PyTuple::new(py, args.iter().map(|arg| convert_token(py, arg.clone())).collect::<Vec<&PyDict>>());
                                            pyfunc.call1(py, (function.name.to_owned(), py_args, walk_scope(py, scope.to_owned())))
                                        },
                                        TokenType::Scope => {
                                            let py_args = convert_token(py, args_result);
                                            pyfunc.call1(py, (function.name.to_owned(), py_args, walk_scope(py, scope.to_owned())))
                                        },
                                        _ => return Token::new_error(TokenType::SyntaxError, "Function payload must be list or scope".to_string())
                                    };

                                    match py_result {
                                        Ok(result) => match result.extract::<&PyDict>(py) {
                                            Ok(result) => convert_to_token(py, result),
                                            Err(error) => Token::new_error(TokenType::Error, format!("{}", error.value(py)))
                                        },
                                        Err(error) => Token::new_error(TokenType::Error, format!("{}", error.value(py)))
                                    }
                                });

                                if check_if_error(&result) {
                                    return result;
                                }
                            } else if let Some(builtin_result) = call_builtin(function.name.to_owned(), args, scope).await {
                                result = builtin_result;

                                if check_if_error(&result) {
                                    return result;
                                }
                            }
                        } else {
                            if node.children.is_empty() {
                                return Token::new_error(TokenType::Undefined, format!("Variable '{}' is not defined", node.token.value));
                            }

                            if node.children.get(0).unwrap()._type != ASTType::Assign {
                                return Token::new_error(TokenType::Undefined, format!("Variable '{}' is not defined", node.token.value));
                            }

                            result = execute_ast(node.children, scope, Some(node.token.to_owned()), depth).await;

                            if check_if_error(&result) {
                                return result;
                            }
                        }
                    },
                    TokenType::Dot => {
                        result = execute_ast(node.children, scope, Some(context.to_owned()), depth).await;

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

                let value = execute_ast(node.children, scope, Some(context.to_owned()), depth).await;

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
                        value: value.to_owned()
                    });
                }
            },
            ASTType::Expression => {
                if let Some(variable) = get_variable(&context.value, scope) {
                    context = variable.value.to_owned();
                } else if context._type == TokenType::Var {
                    return Token::new_error(TokenType::SyntaxError, "Cannot assign to a variable outside of scope".to_string());
                }

                let mut _result = Token::new_int(context.number);

                let children_result = execute_ast(node.children, scope, Some(_result.to_owned()), depth).await;

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
            ASTType::Equation => {
                let mut stack: Vec<Token> = Vec::new();

                for children in node.children {
                    match children.token._type {
                        TokenType::Plus |
                        TokenType::Minus |
                        TokenType::Multiply |
                        TokenType::Divide |
                        TokenType::Modulo => {
                            let stack_len = stack.len();
                            
                            let left = stack[stack_len - 2].to_owned();
                            let right = stack[stack_len - 1].to_owned();

                            stack.remove(stack_len - 1);
                            stack.remove(stack_len - 2);

                            stack.push(Token::new_int(match children.token._type {
                                TokenType::Plus => left.number + right.number,
                                TokenType::Minus => left.number - right.number,
                                TokenType::Multiply => left.number * right.number,
                                TokenType::Divide => left.number / right.number,
                                TokenType::Modulo => left.number % right.number,
                                _ => unreachable!()
                            }))
                        },
                        TokenType::Var => {
                            result = execute_ast(vec![children], scope, None, depth).await;
                            
                            if check_if_error(&result) {
                                return result;
                            }

                            stack.push(result);
                        },
                        _ => stack.push(children.token)
                    }
                }

                result = stack[0].to_owned();
            },
            ASTType::Keyword => {
                match node.token._type {
                    TokenType::If => {
                        let condition = execute_ast(node.children[0].children.to_owned(), scope, Some(Token::new(TokenType::If)), depth).await;

                        if check_if_error(&condition) {
                            return condition;
                        }

                        if condition.number == 1.0 {
                            result = execute_ast(node.children[1].children.to_owned(), scope, Some(Token::new(TokenType::If)), depth).await;
                        } else if node.children.len() == 3 {
                            result = execute_ast(node.children[2].children.to_owned(), scope, Some(Token::new(TokenType::If)), depth).await;
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
                            builtin: false,
                            pyfunc: None
                        });
                    },
                    TokenType::Return => {
                        result = execute_ast(node.children, scope, None, depth).await;

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