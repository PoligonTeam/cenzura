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

#![warn(clippy::pedantic)]

use crate::utils::*;
use std::collections::HashMap;
use pyo3::{prelude::*, types::PyDict, types::PyList};

mod lexer;
mod parser;
mod interpreter;
mod builtins;
mod utils;

#[pyfunction]
fn generate_tokens(py: Python, code: String) -> PyResult<Vec<&PyDict>> {
    let tokens = lexer::generate_tokens(&code);

    let mut py_tokens = Vec::new();

    for token in tokens {
        py_tokens.push(convert_token(py, token));
    }

    Ok(py_tokens)
}

#[pyfunction]
fn generate_ast<'a>(py: Python<'a>, tokens: Vec<&PyDict>) -> PyResult<Vec<&'a PyDict>> {
    let mut rust_tokens: Vec<lexer::Token> = Vec::new();

    for token in tokens {
        rust_tokens.push(convert_to_token(py, token));
    }

    let ast = parser::generate_ast(rust_tokens.iter().collect());

    Ok(convert_ast(py, ast))
}

static mut FUNCTIONS: Option<HashMap<String, PyObject>> = None;

#[pyfunction]
fn execute_ast<'a>(py: Python<'a>, ast: Vec<&PyDict>, variables: Vec<&PyDict>, functions: Vec<&PyDict>) -> PyResult<&'a PyDict> {
    let rust_ast = convert_to_ast(py, ast);

    let mut builtins = builtins::get_builtins();

    fn get_scope(py: Python, variables: Vec<&PyDict>) -> interpreter::Scope {
        let mut scope = interpreter::Scope::new();

        for variable in variables {
            let name = variable.get_item("name").unwrap().extract::<String>().unwrap();
            let value = convert_to_token(py, variable.get_item("value").unwrap().extract::<&PyDict>().unwrap());

            scope.push_variable(&name, value, if let Some(child_variables) = variable.get_item("variables") {
                Some(get_scope(py, child_variables.extract::<Vec<&PyDict>>().unwrap()))
            } else {
                None
            });
        }

        scope
    }

    let mut scope = get_scope(py, variables);

    scope.functions.append(&mut builtins);

    unsafe {
        FUNCTIONS = Some(HashMap::new());
    }

    for function in functions {
        let name = function.get_item("name").unwrap().extract::<String>().unwrap();
        let func = function.get_item("func").unwrap().extract::<PyObject>().unwrap();

        unsafe {
            let mut funcs = FUNCTIONS.as_ref().unwrap().to_owned();
            funcs.insert(name.to_owned(), func);
            FUNCTIONS = Some(funcs);
        }

        fn wrapper(name: String, args: Vec<lexer::Token>, _scope: interpreter::Scope) -> lexer::Token {
            Python::with_gil(|py| {
                let py_args = PyList::new(py, args.iter().map(|arg| convert_token(py, arg.clone())).collect::<Vec<&PyDict>>());
                let py_scope = PyDict::new(py);

                for variable in _scope.variables {
                    py_scope.set_item(variable.name, convert_token(py, variable.value)).unwrap();
                }

                unsafe {
                    let funcs = FUNCTIONS.as_ref().unwrap();

                    if let Some(func) = funcs.get(&name) {
                        let result = func.call1(py, (name, py_args, py_scope));

                        match result {
                            Ok(result) => match result.extract::<&PyDict>(py) {
                                Ok(result) => convert_to_token(py, result),
                                Err(error) => lexer::Token::new_error(lexer::TokenType::Error, format!("{}", error.value(py)))
                            }
                            Err(error) => lexer::Token::new_error(lexer::TokenType::Error, format!("{}", error.value(py)))
                        }
                    } else {
                        lexer::Token::new_error(lexer::TokenType::Undefined, format!("{} is not defined", name))
                    }
                }
            })
        }

        scope.push_function(&name, wrapper);
    }

    let result = interpreter::execute_ast(rust_ast, &mut scope, None, 0);

    unsafe {
        FUNCTIONS = None;
    }

    Ok(convert_token(py, result))
}

#[pymodule]
fn femscript_rs(_py: Python, module: &PyModule) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(generate_tokens, module)?)?;
    module.add_function(wrap_pyfunction!(generate_ast, module)?)?;
    module.add_function(wrap_pyfunction!(execute_ast, module)?)?;

    Ok(())
}