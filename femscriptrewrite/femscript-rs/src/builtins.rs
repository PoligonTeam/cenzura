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
use crate::interpreter::{Function, Scope};
use crate::utils::convert_to_token;
use rand::Rng;
use pyo3::{prelude::*, types::PyDict};
use pyo3_asyncio;

macro_rules! check_args {
    ($name:ident, $args:ident) => {
        if $args.len() == 0 {
            return Token::new_error(TokenType::TypeError, format!("{}() takes 1 argument", $name));
        }
    };

    ($name:ident, $args:ident, $count:expr) => {
        if $args.len() != $count {
            return Token::new_error(TokenType::TypeError, format!("{}() takes {} arguments", $name, $count));
        }
    };

    ($name:ident, $args:ident, $min:expr, $max:expr) => {
        if $args.len() < $min || $args.len() > $max {
            return Token::new_error(TokenType::TypeError, format!("{}() takes {} to {} arguments", $name, $min, $max));
        }
    };
}

pub async fn print(name: String, args: Vec<Token>, _scope: &mut Scope) -> Token {
    check_args!(name, args);

    println!("{}", match args[0]._type {
        TokenType::Str => args[0].value.to_string(),
        TokenType::Int => args[0].number.to_string(),
        TokenType::Bool => match args[0].number as i32 {
            0 => "false".to_string(),
            1 => "true".to_string(),
            _ => unreachable!()
        },
        _ => args[0].to_string()
    });

    Token::new_none()
}

async fn debug(name: String, args: Vec<Token>, _scope: &mut Scope) -> Token {
    check_args!(name, args, 1, 2);

    Token::new_string(
        match args.len() {
            1 => format!("{:?}", args[0]),
            2 => {
                if args[1].number == 0.0 {
                    format!("{:?}", args[0]).to_string()
                } else if args[1].number == 1.0 {
                    format!("{:#?}", args[0]).to_string()
                } else {
                    unreachable!()
                }
            },
            _ => unreachable!()
        }
    )
}

async fn get(name: String, args: Vec<Token>, _scope: &mut Scope) -> Token {
    check_args!(name, args, 2);

    if args[0]._type != TokenType::List {
        return Token::new_error(TokenType::TypeError, "item() takes a list as its first argument".to_string());
    }

    if args[1]._type != TokenType::Int {
        return Token::new_error(TokenType::TypeError, "item() takes an integer as its second argument".to_string());
    }

    let index = args[1].number as usize;

    if index >= args[0].list.len() {
        return Token::new_error(TokenType::TypeError, format!("list index out of range: {}", index));
    }

    args[0].list[index].to_owned()
}

async fn len(name: String, args: Vec<Token>, _scope: &mut Scope) -> Token {
    check_args!(name, args);

    match args[0]._type {
        TokenType::List => Token::new_int(args[0].list.len() as f64),
        TokenType::Str => Token::new_int(args[0].value.len() as f64),
        _ => Token::new_error(TokenType::TypeError, "len() takes a list or string as its first argument".to_string())
    }
}

async fn contains(name: String, args: Vec<Token>, _scope: &mut Scope) -> Token {
    check_args!(name, args, 2);

    if args[0]._type != TokenType::List {
        return Token::new_error(TokenType::TypeError, "has() takes a list as its first argument".to_string());
    }

    if let TokenType::Str | TokenType::Int | TokenType::Bool = args[1]._type {} else {
        return Token::new_error(TokenType::TypeError, "has() takes string, int or bool as its second argument".to_string());
    }

    for token in &args[0].list {
        if match token._type {
            TokenType::Str => token.value == args[1].value,
            TokenType::Int | TokenType::Bool => token.number == args[1].number,
            _ => false
        } {
            return Token::new_bool("true".to_string())
        }
    }

    Token::new_bool("false".to_string())
}

async fn hex(name: String, args: Vec<Token>, _scope: &mut Scope) -> Token {
    check_args!(name, args);

    if args[0]._type != TokenType::Str {
        return Token::new_error(TokenType::TypeError, "hex() takes a string as its first argument".to_string());
    }

    Token::new_int(i64::from_str_radix(&args[0].value, 16).unwrap_or_default() as f64)
}

async fn rgb(name: String, args: Vec<Token>, _scope: &mut Scope) -> Token {
    check_args!(name, args, 3);

    if args[0]._type != TokenType::Int {
        return Token::new_error(TokenType::TypeError, "rgb() takes an integer as its first argument".to_string());
    }

    if args[1]._type != TokenType::Int {
        return Token::new_error(TokenType::TypeError, "rgb() takes an integer as its second argument".to_string());
    }

    if args[2]._type != TokenType::Int {
        return Token::new_error(TokenType::TypeError, "rgb() takes an integer as its third argument".to_string());
    }

    let r = args[0].number as u64;
    let g = args[1].number as u64;
    let b = args[2].number as u64;

    Token::new_int(((r << 16) | (g << 8) | b) as f64)
}

async fn randint(name: String, args: Vec<Token>, _scope: &mut Scope) -> Token {
    check_args!(name, args, 2, 3);

    if args[0]._type != TokenType::Int {
        return Token::new_error(TokenType::TypeError, "randint() takes an int as its first argument".to_string());
    }

    if args[1]._type != TokenType::Int {
        return Token::new_error(TokenType::TypeError, "randint() takes an int as its second argument".to_string());
    }

    let mut rng = rand::thread_rng();
    let mut num = rng.gen::<f64>() * (args[1].number - args[0].number) + args[0].number;

    if args.len() == 3 {
        if args[2]._type != TokenType::Bool {
            return Token::new_error(TokenType::TypeError, "randint() takes a bool as its third argument".to_string());
        }

        if args[2].number == 0.0 {
            num = num.floor()
        }
    } else {
        num = num.floor()
    }

    Token::new_int(num)
}

async fn _format(name: String, args: Vec<Token>, scope: &mut Scope) -> Token {
    check_args!(name, args);

    let mut text = args[0].value.chars().peekable();
    let mut formatted_text = String::new();
    let mut index = 1;

    while let Some(c) = text.next() {
        if c == '{' {
            if let Some(&c) = text.peek() {
                if c == '}' {
                    index += 1;
                    if index > args.len() {
                        return Token::new_error(TokenType::IndexError, "not enough arguments".to_string());
                    }
                    if args[index-1]._type != TokenType::Str {
                        return Token::new_error(TokenType::TypeError, "all arguments must be strings".to_string());
                    }
                    formatted_text += &args[index-1].value;
                    text.next();
                } else {
                    let mut name = String::new();
                    while let Some(c) = text.next() {
                        if c == '}' {
                            let mut found = false;
                            for variable in &scope.variables {
                                if variable.name == name {
                                    if variable.value._type != TokenType::Str {
                                        return Token::new_error(TokenType::TypeError, "all arguments must be strings".to_string());
                                    }
                                    formatted_text += &variable.value.value;
                                    found = true;
                                    break
                                }
                            }
                            if !found {
                                return Token::new_error(TokenType::Undefined, format!("{} is not defined", name));
                            }
                            break
                        } else {
                            name += &c.to_string();
                        }
                    }
                }
            } else {
                return Token::new_error(TokenType::SyntaxError, "missing }".to_string());
            }
        } else {
            formatted_text += &c.to_string();
        }
    }

    Token::new_string(formatted_text)
}

async fn _type(name: String, args: Vec<Token>, _scope: &mut Scope) -> Token {
    check_args!(name, args);

    Token::new_string(format!("{:?}", args[0]._type))
}

async fn _str(name: String, args: Vec<Token>, _scope: &mut Scope) -> Token {
    check_args!(name, args);

    match args[0]._type {
        TokenType::Str => args[0].to_owned(),
        TokenType::Int => Token::new_string(args[0].number.to_string()),
        TokenType::Bool => Token::new_string(if args[0].number == 1.0 { "true "} else { "false" }.to_string()),
        _ => Token::new_error(TokenType::Unsupported, format!("{:?} type is not supported", args[0]._type))
    }
}

pub async fn _await(name: String, args: Vec<Token>, _scope: &mut Scope) -> Token {
    check_args!(name, args);

    if let None = args[0].pyobject {
        return Token::new_error(TokenType::TypeError, "await() takes coroutine as its first argument".to_string());
    }

    if let Err(error) = Python::with_gil(|py| {
        if args[0].pyobject.to_owned().unwrap().getattr(py, "__class__").unwrap().getattr(py, "__name__").unwrap().extract::<String>(py).unwrap() != "coroutine" {
            return Err(Token::new_error(TokenType::TypeError, "await() takes coroutine as its first argument".to_string()));
        }

        Ok(())
    }) {
        return error;
    };

    let future = Python::with_gil(|py| {
        let coro = args[0].pyobject.to_owned().unwrap();
        let locals = pyo3_asyncio::tokio::get_current_locals(py).unwrap();

        pyo3_asyncio::into_future_with_locals(&locals, coro.as_ref(py)).unwrap()
    });

    match future.await {
        Ok(result) => Python::with_gil(|py| convert_to_token(py, result.extract::<&PyDict>(py).unwrap())),
        Err(error) => return Token::new_error(TokenType::Error, error.to_string())
    }
}

pub fn get_builtins() -> Vec<Function> {
    vec![
        Function::new_builtin("get"),
        Function::new_builtin("len"),
        Function::new_builtin("contains"),
        Function::new_builtin("hex"),
        Function::new_builtin("rgb"),
        Function::new_builtin("randint"),
        Function::new_builtin("format"),
        Function::new_builtin("type"),
        Function::new_builtin("str"),
        Function::new_builtin("await")
    ]
}

pub async fn call_builtin(name: String, args: Vec<Token>, scope: &mut Scope) -> Option<Token> {
    macro_rules! wrap {
        ($func:ident) => {
            if stringify!($func) == name {
                return Some($func(name, args, scope).await);
            }
        };

        ($func:ident, $func_name:literal) => {
            if $func_name == name {
                return Some($func(name, args, scope).await);
            }
        };
    }

    wrap!(print);
    wrap!(debug);
    wrap!(get);
    wrap!(len);
    wrap!(contains);
    wrap!(hex);
    wrap!(rgb);
    wrap!(randint);
    wrap!(_format, "format");
    wrap!(_type, "type");
    wrap!(_str, "str");
    wrap!(_await, "await");

    None
}