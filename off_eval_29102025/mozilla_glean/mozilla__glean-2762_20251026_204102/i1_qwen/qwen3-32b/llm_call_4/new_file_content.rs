#tools/embedded-uniffi-bindgen/src/main.rs
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

use std::env;

use anyhow::{bail, Context};
use camino::Utf8PathBuf;
use uniffi::{generate_bindings, TargetLanguage};
use uniffi_bindgen::BindingGeneratorDefault;

fn parse_language(lang: &str) -> anyhow::Result<uniffi::TargetLanguage> {
    match lang {
        "kotlin" => Ok(TargetLanguage::Kotlin),
        "python" => Ok(TargetLanguage::Python),
        "swift" => Ok(TargetLanguage::Swift),
        _ => bail!("Unknown language"),
    }
}

fn main() -> anyhow::Result<()> {
    let mut args = env::args().skip(1);

    if args.next().as_deref() != Some("generate") {
        bail!("Only the `generate` subcommand is supported.");
    }

    let mut udl_file = None;
    let mut target_languages = vec![];
    let mut out_dir = None;
    let mut config = None;

    while let Some(arg) = args.next() {
        if let Some(arg) = arg.strip_prefix("--") {
            match arg {
                "language" => {
                    let lang = args.next().context("--language needs a parameter")?;
                    let lang = parse_language(&lang)?;
                    target_languages.push(lang);
                }
                "out-dir" => out_dir = Some(args.next().context("--out-dir needs a parameter")?),
                "no-format" => {
                    // this is the default anyway.
                }
                "config" => {
                    config = Some(args.next().context("--config needs a parameter")?);
                }
                _ => bail!("Unsupported option: {arg}"),
            }
        } else if udl_file.is_some() {
            bail!("UDL file already set.");
        } else {
            udl_file = Some(Utf8PathBuf::from(arg));
        }
    }

    let out_dir = out_dir.map(Utf8PathBuf::from);
    let config = config.map(Utf8PathBuf::from);

    if udl_file.is_none() {
        bail!("Need UDL file");
    }

    if target_languages.is_empty() {
        bail!("Need at least one language to generate code for.");
    }

    if out_dir.is_none() {
        bail!("Need output directory.")
    }

    let generator = BindingGeneratorDefault {
        target_languages,
        try_format_code: false,
    };

    generate_bindings(
        &udl_file.unwrap(),
        config.as_deref(),
        generator,
        out_dir.as_deref(),
        None,
        Some("glean_core"),
        false,
    )?;

    Ok(())
}

#[cfg(test)]
mod tests {
use std::env;
use std::fs;
use std::path::PathBuf;
use super::main;

#[test]
fn test_generator_initialization_success_with_valid_udl() {
    let temp_dir = env::temp_dir();
    let tmp_dir = temp_dir.join("embedded_uniffi_test");
    fs::create_dir_all(&tmp_dir).unwrap();

    let udl_file_path = tmp_dir.join("test.udl");
    fs::write(&udl_file_path, "namespace glean_core;\nerror MyError { Message };").unwrap();
    let out_dir_path = tmp_dir.join("out");
    fs::create_dir_all(&out_dir_path).unwrap();

    env::set_var("UDL_FILE", udl_file_path.to_str().unwrap());
    env::set_var("OUT_DIR", out_dir_path.to_str().unwrap());
    env::set_var("TARGET_LANGUAGE", "Rust");

    let result = main();
    assert!(result.is_ok());
}
}
