#tools/embedded-uniffi-bindgen/src/lib.rs
// intentionally left empty. only exists to make a warning go away

#[cfg(test)]
mod tests {
use std::fs;
use std::path::Path;

#[test]
fn test_file_exists() {
    let path = Path::new("tools/embedded-uniffi-bindgen/src/lib.rs");
    let expected_content = "// intentionally left empty. only exists to make a warning go away";
    let expected = true;
    let actual = path.exists() && fs::read_to_string(path).unwrap().trim() == expected_content;
    assert_eq!(expected, actual);
}
}
