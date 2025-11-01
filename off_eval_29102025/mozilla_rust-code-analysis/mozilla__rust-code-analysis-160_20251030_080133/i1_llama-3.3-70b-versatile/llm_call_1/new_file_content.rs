#src/output/dump_formats.rs
use regex::Regex;
use std::fs::File;
use std::io::Write;
use std::io::{Error, ErrorKind};
use std::path::PathBuf;
use std::str::FromStr;

use crate::spaces::FuncSpace;

#[derive(Debug, Clone)]
pub enum Format {
    Cbor,
    Json,
    Toml,
    Yaml,
}

impl Format {
    pub fn all() -> &'static [&'static str] {
        &["cbor", "json", "toml", "yaml"]
    }
}

impl FromStr for Format {
    type Err = String;

    fn from_str(format: &str) -> Result<Self, Self::Err> {
        match format {
            "cbor" => Ok(Format::Cbor),
            "json" => Ok(Format::Json),
            "toml" => Ok(Format::Toml),
            "yaml" => Ok(Format::Yaml),
            format => Err(format!("{:?} is not a supported format", format)),
        }
    }
}

pub(crate) fn dump_formats(
    space: &FuncSpace,
    path: &PathBuf,
    output_path: &Option<PathBuf>,
    output_format: Format,
    pretty: bool,
) -> std::io::Result<()> {
    if output_path.is_none() {
        let stdout = std::io::stdout();
        let mut stdout = stdout.lock();

        match output_format {
            Format::Cbor => Err(Error::new(
                ErrorKind::Other,
                "Cbor format cannot be printed to stdout",
            )),
            Format::Json => {
                let json_data = if pretty {
                    serde_json::to_string_pretty(&space).unwrap()
                } else {
                    serde_json::to_string(&space).unwrap()
                };
                write!(stdout, "{}", json_data)
            }
            Format::Toml => {
                let toml_data = if pretty {
                    toml::to_string_pretty(&space).unwrap()
                } else {
                    toml::to_string(&space).unwrap()
                };
                write!(stdout, "{}", toml_data)
            }
            Format::Yaml => write!(stdout, "{}", serde_yaml::to_string(&space).unwrap()),
        }
    } else {
        let format_ext = match output_format {
            Format::Cbor => ".cbor",
            Format::Json => ".json",
            Format::Toml => ".toml",
            Format::Yaml => ".yml",
        };

        let output_path = output_path.as_ref().unwrap();

        let mut file = path.as_path().file_name().unwrap().to_os_string();
        file.push(format_ext);

        let mut format_path = output_path.clone();
        format_path.push(file);

        if format_path.as_path().exists() {
            let mut new_filename = path.to_str().unwrap().to_string();
            let re = Regex::new(r"[\\:/]").unwrap();
            new_filename = re.replace_all(&new_filename, "_").to_string();
            new_filename.push_str(format_ext);
            format_path.pop();
            format_path.push(new_filename);
        }

        let mut format_file = File::create(format_path)?;
        match output_format {
            Format::Cbor => serde_cbor::to_writer(format_file, &space)
                .map_err(|e| Error::new(ErrorKind::Other, e.to_string())),
            Format::Json => {
                if pretty {
                    serde_json::to_writer_pretty(format_file, &space)
                        .map_err(|e| Error::new(ErrorKind::Other, e.to_string()))
                } else {
                    serde_json::to_writer(format_file, &space)
                        .map_err(|e| Error::new(ErrorKind::Other, e.to_string()))
                }
            }
            Format::Toml => {
                let toml_data = if pretty {
                    toml::to_string_pretty(&space).unwrap()
                } else {
                    toml::to_string(&space).unwrap()
                };
                format_file.write_all(toml_data.as_bytes())
            }
            Format::Yaml => serde_yaml::to_writer(format_file, &space)
                .map_err(|e| Error::new(ErrorKind::Other, e.to_string())),
        }
    }
}

#[cfg(test)]
mod tests {
use std::io::Write;
use crate::spaces::FuncSpace;
use crate::spaces::CodeMetrics;
use crate::output::dump_formats::dump_formats;
use crate::output::dump_formats::Format;
use serde_json;

#[test]
fn test_dump_json_to_stdout() {
  let space = FuncSpace {
    name: None,
    kind: crate::spaces::SpaceKind::Function,
    start_line: 1,
    end_line: 10,
    spaces: vec![],
    metrics: CodeMetrics {
      nargs: crate::fn_args::Stats { n_args: 0 },
      nexits: crate::exit::Stats { exit: 0 },
      cyclomatic: crate::cyclomatic::Stats { cyclomatic: 0.0 },
      halstead: crate::halstead::Stats { u_operators: 0, operators: 0, u_operands: 0, operands: 0 },
      loc: crate::loc::Stats { sloc: 0, ploc: 0, lloc: 0, cloc: 0, blank: 0 },
      nom: crate::nom::Stats { functions: 0, closures: 0, total: 0 },
      mi: crate::mi::Stats { mi_original: 0.0, mi_sei: 0.0, mi_visual_studio: 0.0 },
    },
  };
  let path = std::path::PathBuf::from("test_file");
  let output_path = None;
  let output_format = Format::Json;
  let pretty = true;

  let mut stdout = std::io::stdout();
  dump_formats(&space, &path, &output_path, output_format, pretty).unwrap();

  let expected_json = serde_json::to_string_pretty(&space).unwrap();
  let mut actual_json = String::new();
  stdout.lock().read_to_string(&mut actual_json).unwrap();

  assert_eq!(expected_json, actual_json);
}
}
