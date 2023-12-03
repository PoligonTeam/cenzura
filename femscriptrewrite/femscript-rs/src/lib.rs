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
use pyo3::{prelude::*, types::{PyDict, PyBool}};

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

#[pyfunction]
fn execute_ast<'a>(py: Python<'a>, ast: Vec<&PyDict>, variables: Vec<&PyDict>, functions: Vec<&PyDict>, debug: &PyBool) -> PyResult<&'a PyAny> {
    let rust_ast = convert_to_ast(py, ast);

    let mut scope = utils::get_scope(py, variables);
    let mut builtins = builtins::get_builtins();

    scope.functions.append(&mut builtins);

    if debug.is_true() {
        scope.functions.push(interpreter::Function::new_builtin("print"));
        scope.functions.push(interpreter::Function::new_builtin("debug"));
    }

    for function in functions {
        let name = function.get_item("name").unwrap().extract::<String>().unwrap();
        let func = function.get_item("func").unwrap().extract::<PyObject>().unwrap();

        scope.push_pyfunc(&name, func);
    }

    pyo3_asyncio::tokio::future_into_py(py, async move {
        let result = interpreter::execute_ast(rust_ast, &mut scope, None, 0).await;

        Ok(Python::with_gil(|py| convert_token(py, result).as_ref().to_object(py).clone()))
    })
}

#[pymodule]
fn femscript_rs(_py: Python, module: &PyModule) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(generate_tokens, module)?)?;
    module.add_function(wrap_pyfunction!(generate_ast, module)?)?;
    module.add_function(wrap_pyfunction!(execute_ast, module)?)?;

    Ok(())
}