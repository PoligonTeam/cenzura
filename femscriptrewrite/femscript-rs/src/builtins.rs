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
use crate::interpreter::{Scope, Function};

macro_rules! check_args {
    ($args:ident) => {
        if $args.len() == 0 {
            return Token::new_error(TokenType::TypeError, "print() takes 1 argument".to_string());
        }
    };

    ($args:ident, $count:expr) => {
        if $args.len() != $count {
            return Token::new_error(TokenType::TypeError, format!("print() takes {} arguments", $count));
        }
    };

    ($args:ident, $min:expr, $max:expr) => {
        if $args.len() < $min || $args.len() > $max {
            return Token::new_error(TokenType::TypeError, format!("print() takes {} to {} arguments", $min, $max));
        }
    };
}

pub fn print(_name: String, args: Vec<Token>, _scope: Scope) -> Token {
    check_args!(args);

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

pub fn debug(_name: String, args: Vec<Token>, _scope: Scope) -> Token {
    check_args!(args, 1, 2);

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

pub fn get(_name: String, args: Vec<Token>, _scope: Scope) -> Token {
    check_args!(args, 2);

    if args[0]._type != TokenType::List {
        return Token::new_error(TokenType::TypeError, "item() takes a list as the first argument".to_string());
    }

    if args[1]._type != TokenType::Int {
        return Token::new_error(TokenType::TypeError, "item() takes an integer as the second argument".to_string());
    }

    let index = args[1].number as usize;

    if index >= args[0].list.len() {
        return Token::new_error(TokenType::TypeError, format!("list index out of range: {}", index));
    }

    args[0].list[index].to_owned()
}

pub fn len(_name: String, args: Vec<Token>, _scope: Scope) -> Token {
    check_args!(args);

    match args[0]._type {
        TokenType::List => Token::new_int(args[0].list.len() as f64),
        TokenType::Str => Token::new_int(args[0].value.len() as f64),
        _ => Token::new_error(TokenType::TypeError, "len() takes a list or string as the first argument".to_string())
    }
}

pub fn hex(_name: String, args: Vec<Token>, _scope: Scope) -> Token {
    check_args!(args);

    if args[0]._type != TokenType::Str {
        return Token::new_error(TokenType::TypeError, "hex() takes an string as the first argument".to_string());
    }

    Token::new_int(i64::from_str_radix(&args[0].value, 16).unwrap_or_default() as f64)
}

pub fn rgb(_name: String, args: Vec<Token>, _scope: Scope) -> Token {
    check_args!(args, 3);

    if args[0]._type != TokenType::Int {
        return Token::new_error(TokenType::TypeError, "rgb() takes an integer as the first argument".to_string());
    }

    if args[1]._type != TokenType::Int {
        return Token::new_error(TokenType::TypeError, "rgb() takes an integer as the second argument".to_string());
    }

    if args[2]._type != TokenType::Int {
        return Token::new_error(TokenType::TypeError, "rgb() takes an integer as the third argument".to_string());
    }

    let r = args[0].number as u64;
    let g = args[1].number as u64;
    let b = args[2].number as u64;

    Token::new_int(((r << 16) | (g << 8) | b) as f64)
}

pub fn get_builtins() -> Vec<Function> {
    vec![
        Function::new_builtin("print", print),
        Function::new_builtin("debug", debug),
        Function::new_builtin("get", get),
        Function::new_builtin("len", len),
        Function::new_builtin("hex", hex),
        Function::new_builtin("rgb", rgb)
    ]
}