#src/output/dump_formats.rs
#[cfg(test)]
mod tests {
use serde_json::Value;
use std::process::Command;

#[test]
fn test_dump_json_to_stdout() {
    let output = Command::new("target/debug/code-analysis")
        .args(["--metrics", "--output-format", "json", "tests/fixtures/empty.rs"])
        .output()
        .unwrap();

    assert_eq!(output.status.code().unwrap(), 0);

    let json: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert!(json.is_object());
}
}
