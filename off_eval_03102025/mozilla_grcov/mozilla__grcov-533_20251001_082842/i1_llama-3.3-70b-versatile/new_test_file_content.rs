#src/bin/cargo-grcov.rs
#[cfg(test)]
mod tests {
use super::parse_args;
use super::acts;
use super::Context;
use super::action::Action;
use super::Action;
use super::Action::{SetupEnv, Report};
use super::SetupEnv;
use super::Report;
use std::env;
use std::path::PathBuf;
use std::process;
use std::ffi::OsString;
use std::collections::HashMap;

#[test]
fn test_cargo_grcov_command() {
    let mut context = Context {
        pwd: PathBuf::from("/"),
        args: vec![OsString::from("cargo"), OsString::from("grcov"), OsString::from("report")],
        env: HashMap::new(),
    };
    let actions = parse_args(context.clone()).unwrap();
    assert!(actions.len() > 0);
    match acts(&actions) {
        Ok(_) => (),
        Err(_) => process::exit(1),
    }
}
}
