#tools/embedded-uniffi-bindgen/src/lib.rs
#[cfg(test)]
mod tests {
use std::fs;
use std::io::Write;
use std::path::Path;

#[test]
fn test_embedded_uniffi_bindgen_exists() {
  let path = Path::new("tools/embedded-uniffi-bindgen/lib.rs");
  assert!(path.exists());
  let metadata = fs::metadata(path).unwrap();
  assert!(metadata.len() > 0);
}
}
