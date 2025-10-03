#tools/embedded-uniffi-bindgen/src/lib.rs
#[cfg(test)]
mod tests {
use std::fs;
use std::path::Path;

#[test]
fn test_lib_file_exists() {
    let path = Path::new("tools/embedded-uniffi-bindgen/lib.rs");
    let expected = true;
    let actual = path.exists() && fs::read_to_string(path).unwrap().is_empty();
    assert_eq!(expected, actual);
}
}
