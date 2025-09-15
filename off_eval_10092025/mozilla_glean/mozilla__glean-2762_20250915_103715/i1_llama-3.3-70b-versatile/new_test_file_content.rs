#tools/embedded-uniffi-bindgen/src/main.rs
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

use std::env;

use anyhow::{bail, Context};
use camino::Utf8PathBuf;
use uniffi::{generate_bindings, TargetLanguage};

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

    generate_bindings(
        &udl_file.unwrap(),
        config.as_deref(),
        target_languages,
        out_dir.as_deref(),
        None,
        Some("glean_core"),
        false,
    )?;

    Ok(())
}

#[cfg(test)]
mod tests {
use super::main;
use std::env;
use anyhow::{bail, Context};
use camino::Utf8PathBuf;
use uniffi::{generate_bindings, TargetLanguage};
use uniffi_bindgen::BindingGeneratorDefault;

#[test]
fn test_binding_generator() {
  let udl_file = "path_to_udl_file";
  let config = None;
  let target_languages = vec![TargetLanguage::Rust];
  let out_dir = "path_to_out_dir";
  let result_before_patch = std::panic::catch_unwind(|| main());
  assert!(result_before_patch.is_err());
  let generator = BindingGeneratorDefault {
    target_languages,
    try_format_code: false,
  };
  let result_after_patch = std::panic::catch_unwind(|| {
    generate_bindings(
      &udl_file,
      config.as_deref(),
      generator,
      out_dir,
      None,
      Some("glean_core"),
    )
  });
  assert!(result_after_patch.is_ok());
}
}
