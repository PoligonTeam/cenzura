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
use anyhow::{Result, bail};
use std::iter::Peekable;
use std::slice::Iter;
use std::str::FromStr;

#[allow(dead_code)]
#[derive(Clone, PartialEq, Debug)]
pub enum ASTType {
    Block,
    Assign,
    Token,
    Expression,
    Keyword,
    Error
}

#[allow(dead_code)]
impl FromStr for ASTType {
    type Err = ();

    fn from_str(string: &str) -> Result<Self, Self::Err> {
        macro_rules! match_string {
            ($($variant:ident),*) => {
                match string {
                    $(
                        stringify!($variant) => Ok(Self::$variant),
                    )*
                    _ => Err(())
                }
            };
        }

        match_string!(
            Block,
            Assign,
            Token,
            Expression,
            Keyword,
            Error
        )
    }
}

#[derive(Clone, Debug)]
pub struct AST {
    pub _type: ASTType,
    pub token: Token,
    pub children: Vec<AST>
}

fn get_tokens_in_expr<'a, 'b>(tokens: &'a mut Peekable<Iter<&'b Token>>, to: TokenType, or_to: Option<TokenType>) -> Result<Vec<&'b Token>> {
    let mut tokens_in_expr: Vec<&Token> = Vec::new();

    while let Some(token) = tokens.next() {
        if token._type == to {
            return Ok(tokens_in_expr);
        } else if let Some(ref or_to) = or_to {
            if token._type == *or_to {
                return Ok(tokens_in_expr);
            }
        } else if token._type == TokenType::LeftBrace {
            tokens_in_expr.push(token);
            tokens_in_expr.append(match &mut get_tokens_in_block(tokens, &mut 1) {
                Ok(tokens) => tokens,
                Err(error) => bail!(error.to_string())
            });
            continue;
        }

        tokens_in_expr.push(token);
    }

    Ok(tokens_in_expr)
}

fn get_tokens_in_block<'a, 'b>(tokens: &'a mut Peekable<Iter<&'b Token>>, count: &mut i32) -> Result<Vec<&'b Token>> {
    let mut tokens_in_block: Vec<&'b Token> = Vec::new();

    while let Some(token) = tokens.next() {
        if token._type == TokenType::LeftBrace {
            *count += 1;
        } else if token._type == TokenType::RightBrace {
            *count -= 1;
        } else {
            tokens_in_block.push(token);
        }

        if *count == 0 {
            return Ok(tokens_in_block);
        }
    }

    if *count != 1 {
        bail!("missing {:?}", TokenType::RightBrace)
    }

    Ok(tokens_in_block)
}

fn get_ast_in_list<'a, 'b>(tokens: &'a mut Peekable<Iter<&'b Token>>, from: TokenType, to: TokenType) -> Result<Vec<AST>> {
    let mut ast_in_list: Vec<AST> = Vec::new();

    while let Some(token) = tokens.next() {
        if token._type == from {
            let ast = get_ast_in_list(tokens, from.clone(), to.clone());

            ast_in_list.push(match ast {
                Ok(ast) => AST {
                    _type: ASTType::Token,
                    token: Token::new(TokenType::List),
                    children: ast
                },
                Err(error) => AST {
                    _type: ASTType::Error,
                    token: Token::new_error(TokenType::SyntaxError, error.to_string()),
                    children: Vec::new()
                }
            });
        } else if token._type == TokenType::Comma || token._type == TokenType:: RightParen || token._type == to {
            return Ok(ast_in_list);
        } else {
            ast_in_list.push(AST {
                _type: match token._type {
                    TokenType::Error |
                    TokenType::Undefined |
                    TokenType::SyntaxError |
                    TokenType::TypeError => ASTType::Error,
                    TokenType::Not => ASTType::Expression,
                    _ => ASTType::Token
                },
                token: token.to_owned().to_owned(),
                children: match get_ast_in_list(tokens, from.to_owned(), to.to_owned()) {
                    Ok(ast) => ast,
                    Err(error) => vec![AST {
                        _type: ASTType::Error,
                        token: Token::new_error(TokenType::SyntaxError, error.to_string()),
                        children: Vec::new()
                    }]
                }
            });
        }
    }

    Ok(ast_in_list)
}

pub fn generate_ast(tokens: Vec<&Token>) -> Vec<AST> {
    let mut ast: Vec<AST> = Vec::new();

    let mut tokens = tokens.iter().peekable();

    while let Some(token) = tokens.next() {
        match token._type {
            TokenType::Error |
            TokenType::Undefined |
            TokenType::RecursionError |
            TokenType::SyntaxError |
            TokenType::TypeError => {
                ast.push(AST {
                    _type: ASTType::Error,
                    token: token.to_owned().to_owned(),
                    children: Vec::new()
                });
            },
            TokenType::RightParen |
            TokenType::RightBracket |
            TokenType::RightBrace => {
                ast.push(AST {
                    _type: ASTType::Error,
                    token: Token::new_error(TokenType::SyntaxError, format!("unmatched {:?}", token._type)),
                    children: Vec::new()
                })
            },
            TokenType::Plus |
            TokenType::Minus |
            TokenType::Multiply |
            TokenType::Divide |
            TokenType::Modulo |
            TokenType::EqualTo |
            TokenType::NotEqual |
            TokenType::Greater |
            TokenType::GreaterEqual |
            TokenType::Less |
            TokenType::LessEqual |
            TokenType::And |
            TokenType::Or |
            TokenType::Not => {
                ast.push(match get_tokens_in_expr(&mut tokens, TokenType::Semicolon, None) {
                    Ok(tokens) => AST {
                        _type: ASTType::Expression,
                        token: token.to_owned().to_owned(),
                        children: generate_ast(tokens)
                    },
                    Err(error) => AST {
                        _type: ASTType::Error,
                        token: Token::new_error(TokenType::SyntaxError, error.to_string()),
                        children: Vec::new()
                    }
                });
            },
            TokenType::Equal |
            TokenType::PlusEqual |
            TokenType::MinusEqual |
            TokenType::MultiplyEqual |
            TokenType::DivideEqual |
            TokenType::ModuloEqual => {
                ast.push(match get_tokens_in_expr(&mut tokens, TokenType::Semicolon, None) {
                    Ok(tokens) => AST {
                        _type: ASTType::Assign,
                        token: token.to_owned().to_owned(),
                        children: generate_ast(tokens)
                    },
                    Err(error) => AST {
                        _type: ASTType::Error,
                        token: Token::new_error(TokenType::SyntaxError, error.to_string()),
                        children: Vec::new()
                    }
                });
            },
            TokenType::Var => {
                ast.push(match get_tokens_in_expr(&mut tokens, TokenType::Semicolon, None) {
                    Ok(tokens) => AST {
                        _type: ASTType::Token,
                        token: token.to_owned().to_owned(),
                        children: generate_ast(tokens)
                    },
                    Err(error) => AST {
                        _type: ASTType::Error,
                        token: Token::new_error(TokenType::SyntaxError, error.to_string()),
                        children: Vec::new()
                    }
                });
            },
            TokenType::Dot => {
                ast.push(match get_tokens_in_expr(&mut tokens, TokenType::Semicolon, None) {
                    Ok(tokens) => AST {
                        _type: ASTType::Token,
                        token: token.to_owned().to_owned(),
                        children: generate_ast(tokens)
                    },
                    Err(error) => AST {
                        _type: ASTType::Error,
                        token: Token::new_error(TokenType::SyntaxError, error.to_string()),
                        children: Vec::new()
                    }
                });
            },
            TokenType::If => {
                let mut if_ast = AST {
                    _type: ASTType::Keyword,
                    token: token.to_owned().to_owned(),
                    children: vec![match get_tokens_in_block(&mut tokens, &mut 0) {
                        Ok(tokens) => AST {
                            _type: ASTType::Block,
                            token: Token::new(TokenType::Unknown),
                            children: generate_ast(tokens)
                        },
                        Err(error) => AST {
                            _type: ASTType::Error,
                            token: Token::new_error(TokenType::SyntaxError, error.to_string()),
                            children: Vec::new()
                        }
                    }, match get_tokens_in_block(&mut tokens, &mut 0) {
                        Ok(tokens) => AST {
                            _type: ASTType::Block,
                            token: Token::new(TokenType::Unknown),
                            children: generate_ast(tokens)
                        },
                        Err(error) => AST {
                            _type: ASTType::Error,
                            token: Token::new_error(TokenType::SyntaxError, error.to_string()),
                            children: Vec::new()
                        }
                    }]
                };

                if let Some(token) = tokens.peek() {
                    if token._type == TokenType::Else {
                        tokens.next();
                        if_ast.children.push(match get_tokens_in_block(&mut tokens, &mut 0) {
                            Ok(tokens) => AST {
                                _type: ASTType::Block,
                                token: Token::new(TokenType::Unknown),
                                children: generate_ast(tokens)
                            },
                            Err(error) => AST {
                                _type: ASTType::Error,
                                token: Token::new_error(TokenType::SyntaxError, error.to_string()),
                                children: Vec::new()
                            }
                        });
                    }
                }

                ast.push(if_ast);
            },
            TokenType::Func => {
                let mut func_ast = AST {
                    _type: ASTType::Keyword,
                    token: token.to_owned().to_owned(),
                    children: Vec::new()
                };

                func_ast.children.push(AST {
                    _type: ASTType::Token,
                    token: tokens.next().unwrap().to_owned().to_owned(),
                    children: Vec::new()
                });

                tokens.next();

                let mut params: Vec<AST> = Vec::new();

                while let Some(token) = tokens.next() {
                    if token._type == TokenType::RightParen {
                        break;
                    } else if token._type == TokenType::Comma {
                        continue;
                    }

                    params.push(AST {
                        _type: ASTType::Token,
                        token: token.to_owned().to_owned(),
                        children: Vec::new()
                    });
                }

                func_ast.children.push(AST {
                    _type: ASTType::Token,
                    token: Token::new(TokenType::List),
                    children: params
                });

                func_ast.children.push(match get_tokens_in_block(&mut tokens, &mut 0) {
                    Ok(tokens) => AST {
                        _type: ASTType::Block,
                        token: Token::new(TokenType::Unknown),
                        children: generate_ast(tokens)
                    },
                    Err(error) => AST {
                        _type: ASTType::Error,
                        token: Token::new_error(TokenType::SyntaxError, error.to_string()),
                        children: Vec::new()
                    }
                });

                ast.push(func_ast);
            },
            TokenType::Return => {
                ast.push(match get_tokens_in_expr(&mut tokens, TokenType::Semicolon, None) {
                    Ok(tokens) => AST {
                        _type: ASTType::Keyword,
                        token: token.to_owned().to_owned(),
                        children: generate_ast(tokens)
                    },
                    Err(error) => AST {
                        _type: ASTType::Error,
                        token: Token::new_error(TokenType::SyntaxError, error.to_string()),
                        children: Vec::new()
                    }
                });
            },
            TokenType::Int |
            TokenType::Str |
            TokenType::Bool |
            TokenType::None => {
                ast.push(match get_tokens_in_expr(&mut tokens, TokenType::Semicolon, None) {
                    Ok(tokens) => AST {
                        _type: ASTType::Token,
                        token: token.to_owned().to_owned(),
                        children: generate_ast(tokens)
                    },
                    Err(error) => AST {
                        _type: ASTType::Error,
                        token: Token::new_error(TokenType::SyntaxError, error.to_string()),
                        children: Vec::new()
                    }
                });
            },
            TokenType::LeftParen => {
                ast.push(AST {
                    _type: ASTType::Token,
                    token: Token::new(TokenType::List),
                    children: match get_ast_in_list(&mut tokens, TokenType::LeftParen, TokenType::RightParen) {
                        Ok(ast) => ast,
                        Err(error) => vec![AST {
                            _type: ASTType::Error,
                            token: Token::new_error(TokenType::SyntaxError, error.to_string()),
                            children: Vec::new()
                        }]
                    }
                });
            },
            TokenType::LeftBracket => {
                ast.push(AST {
                    _type: ASTType::Token,
                    token: Token::new(TokenType::List),
                    children: match get_ast_in_list(&mut tokens, TokenType::LeftBracket, TokenType::RightBracket) {
                        Ok(ast) => ast,
                        Err(error) => vec![AST {
                            _type: ASTType::Error,
                            token: Token::new_error(TokenType::SyntaxError, error.to_string()),
                            children: Vec::new()
                        }]
                    }
                });
            },
            TokenType::LeftBrace => {
                ast.push(match get_tokens_in_block(&mut tokens, &mut 1) {
                    Ok(tokens) => AST {
                        _type: ASTType::Block,
                        token: Token::new(TokenType::Unknown),
                        children: generate_ast(tokens)
                    },
                    Err(error) => AST {
                        _type: ASTType::Error,
                        token: Token::new_error(TokenType::SyntaxError, error.to_string()),
                        children: Vec::new()
                    }
                });
            },
            _ => {}
        };
    }

    ast
}