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

use std::iter::Peekable;
use std::str::Chars;
use std::fmt::Display;
use std::str::FromStr;
use pyo3::{prelude::Py, types::PyAny};

#[allow(dead_code)]
#[derive(Clone, PartialEq, Debug)]
pub enum TokenType {
    Unknown,

    LeftParen, RightParen,
    LeftBracket, RightBracket,
    LeftBrace, RightBrace,
    Comma, Dot, Colon, Semicolon,
    Plus, Minus, Multiply, Divide, Modulo,
    Equal, PlusEqual, MinusEqual, MultiplyEqual, DivideEqual, ModuloEqual,
    EqualTo, NotEqual, Not, Greater, Less, GreaterEqual, LessEqual,
    Comment,

    If, Else,
    And, Or,
    Func, Import,
    Return,

    Var, Str, Int,
    Bool, None,
    List, Scope,
    PyObject,

    Error, Undefined, RecursionError, SyntaxError, TypeError
}

#[allow(dead_code)]
impl FromStr for TokenType {
    type Err = ();

    fn from_str(string: &str) -> Result<Self, Self::Err> {
        macro_rules! match_string {
            ($($variant:ident),*) => {
                match string {
                    $(
                        stringify!($variant) => Ok(Self::$variant),
                    )*
                    _ => Ok(Self::Unknown)
                }
            };
        }

        match_string!(
            LeftParen, RightParen,
            LeftBracket, RightBracket,
            LeftBrace, RightBrace,
            Comma, Dot, Colon, Semicolon,
            Plus, Minus, Multiply, Divide, Modulo,
            Equal, PlusEqual, MinusEqual, MultiplyEqual, DivideEqual, ModuloEqual,
            EqualTo, NotEqual, Not, Greater, Less, GreaterEqual, LessEqual,
            Comment,
            If, Else,
            And, Or,
            Func, Import,
            Return,
            Var, Str, Int,
            Bool, None,
            List, Scope,
            PyObject
        )
    }
}

#[derive(Clone, Debug)]
pub struct Token {
    pub _type: TokenType,
    pub value: String,
    pub number: f64,
    pub list: Vec<Token>,
    pub pyobject: Option<Py<PyAny>>
}

impl Display for Token {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", match self._type {
            TokenType::Int => self.number.to_string(),
            TokenType::Str => format!("\"{}\"", self.value.replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")),
            TokenType::Bool => self.value.to_owned(),
            TokenType::None => "none".to_owned(),
            TokenType::List => format!("[{}]", self.list.iter().map(|x| format!("{}", x)).collect::<Vec<String>>().join(", ")),
            _ => self.value.to_owned()
        })
    }
}

impl Token {
    pub fn new(_type: TokenType) -> Self {
        Self {
            _type,
            value: String::new(),
            number: 0.0,
            list: Vec::new(),
            pyobject: None
        }
    }

    pub fn new_error(error_type: TokenType, error_text: String) -> Self {
        Self {
            _type: error_type.to_owned(),
            value: format!("{:?}: {}", error_type, error_text),
            number: 0.0,
            list: Vec::new(),
            pyobject: None
        }
    }

    pub fn new_none() -> Self {
        Self {
            _type: TokenType::None,
            value: String::new(),
            number: 0.0,
            list: Vec::new(),
            pyobject: None
        }
    }

    pub fn new_var(value: String) -> Self {
        Self {
            _type: TokenType::Var,
            value,
            number: 0.0,
            list: Vec::new(),
            pyobject: None
        }
    }

    pub fn new_string(value: String) -> Self {
        Self {
            _type: TokenType::Str,
            value,
            number: 0.0,
            list: Vec::new(),
            pyobject: None
        }
    }

    pub fn new_int(number: f64) -> Self {
        Self {
            _type: TokenType::Int,
            value: String::new(),
            number,
            list: Vec::new(),
            pyobject: None
        }
    }

    pub fn new_bool(value: String) -> Self {
        Self {
            _type: TokenType::Bool,
            value: String::new(),
            number: match value.as_str() {
                "true" => 1.0,
                "false" => 0.0,
                _ => unreachable!()
            },
            list: Vec::new(),
            pyobject: None
        }
    }
}

pub fn generate_tokens(code: &str) -> Vec<Token> {
    let mut tokens: Vec<Token> = Vec::new();
    let mut code = code.chars().peekable();

    fn check_next(code: &mut Peekable<Chars>, type1: TokenType, type2: TokenType, value: char) -> Token {
        if let Some(&c) = code.peek() {
            if c != value {
                Token::new(type1)
            } else {
                code.next();
                Token::new(type2)
            }
        } else {
            Token::new(type1)
        }
    }

    while let Some(c) = code.next() {
        let token = match c {
            '(' => Token::new(TokenType::LeftParen),
            ')' => Token::new(TokenType::RightParen),
            '[' => Token::new(TokenType::LeftBracket),
            ']' => Token::new(TokenType::RightBracket),
            '{' => Token::new(TokenType::LeftBrace),
            '}' => Token::new(TokenType::RightBrace),
            ',' => Token::new(TokenType::Comma),
            '.' => Token::new(TokenType::Dot),
            ':' => Token::new(TokenType::Colon),
            ';' => Token::new(TokenType::Semicolon),
            '+' => check_next(&mut code, TokenType::Plus, TokenType::PlusEqual, '='),
            '-' => {
                if let Some(&c) = code.peek() {
                    if c.is_numeric() {
                        let mut num = String::new();
                        let mut float = false;

                        while let Some(&c) = code.peek() {
                            if c.is_numeric() {
                                num.push(c);
                                code.next();
                            } else if c == '.' {
                                float = true;

                                num.push(c);
                                code.next();

                                while let Some(&c) = code.peek() {
                                    if c.is_numeric() {
                                        num.push(c);
                                        code.next();
                                    } else {
                                        break;
                                    }
                                }

                                break;
                            } else {
                                break;
                            }
                        }

                        if !float {
                            num = format!("{}.0", num);
                        }

                        Token::new_int(num.parse::<f64>().unwrap() * -1.0)
                    } else {
                        check_next(&mut code, TokenType::Minus, TokenType::MinusEqual, '=')
                    }
                } else {
                    check_next(&mut code, TokenType::Minus, TokenType::MinusEqual, '=')
                }
            },
            '*' => check_next(&mut code, TokenType::Multiply, TokenType::MultiplyEqual, '='),
            '/' => check_next(&mut code, TokenType::Divide, TokenType::DivideEqual, '='),
            '%' => check_next(&mut code, TokenType::Modulo, TokenType::ModuloEqual, '='),
            '=' => check_next(&mut code, TokenType::Equal, TokenType::EqualTo, '='),
            '!' => check_next(&mut code, TokenType::Not, TokenType::NotEqual, '='),
            '>' => check_next(&mut code, TokenType::Greater, TokenType::GreaterEqual, '='),
            '<' => check_next(&mut code, TokenType::Less, TokenType::LessEqual, '='),
            '#' => {
                while let Some(c) = code.next() {
                    if c == '\n' {
                        break;
                    }
                }

                Token::new(TokenType::Comment)
            },
            '0'..='9' => {
                let mut num = String::new();
                let mut float = false;
                num.push(c);

                while let Some(&c) = code.peek() {
                    if c.is_digit(10) {
                        num.push(c);
                        code.next();
                    } else if c == '.' {
                        float = true;

                        num.push(c);
                        code.next();

                        while let Some(&c) = code.peek() {
                            if c.is_digit(10) {
                                num.push(c);
                                code.next();
                            } else {
                                break;
                            }
                        }

                        break;
                    } else {
                        break
                    }
                }

                if !float {
                    num = format!("{}.0", num);
                }

                Token::new_int(num.parse::<f64>().unwrap())
            },
            'A'..='z' => {
                let mut string = String::new();
                string.push(c);

                while let Some(&c) = code.peek() {
                    if c.is_alphanumeric() || c == '_' {
                        string.push(c);
                        code.next();
                    } else {
                        break
                    }
                }

                match string.as_str() {
                    "true" => Token::new_bool(string),
                    "false" => Token::new_bool(string),
                    "none" => Token::new_none(),
                    "fn" => Token::new(TokenType::Func),
                    "import" => Token::new(TokenType::Import),
                    "return" => Token::new(TokenType::Return),
                    "if" => Token::new(TokenType::If),
                    "else" => Token::new(TokenType::Else),
                    "and" => Token::new(TokenType::And),
                    "or" => Token::new(TokenType::Or),
                    _ => Token::new_var(string)
                }
            },
            '"' => {
                let mut string = String::new();

                while let Some(&c) = code.peek() {
                    if c == '"' {
                        code.next();
                        break
                    } else {
                        if c == '\n' {
                            tokens.push(Token::new_error(TokenType::SyntaxError, "String not closed".to_string()));
                            return tokens;
                        }

                        if c == '\\' {
                            code.next();

                            if let Some(&c) = code.peek() {
                                match c {
                                    'n' => string.push('\n'),
                                    't' => string.push('\t'),
                                    'r' => string.push('\r'),
                                    '\\' => string.push('\\'),
                                    '"' => string.push('"'),
                                    _ => string.push(c)
                                }
                            }
                        } else {
                            string.push(c);
                        }

                        code.next();
                    }
                }

                Token::new_string(string)
            },
            ' ' | '\n' | '\t' => continue,
            _ => Token::new_error(TokenType::Error, format!("{} is not a valid character", c))
        };

        tokens.push(token);
    }

    tokens
}