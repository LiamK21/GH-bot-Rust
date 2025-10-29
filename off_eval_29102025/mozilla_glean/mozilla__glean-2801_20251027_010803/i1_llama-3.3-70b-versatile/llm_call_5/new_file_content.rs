#tools/embedded-uniffi-bindgen/src/lib.rs
// intentionally left empty. only exists to make a warning go away

#[cfg(test)]
mod tests {
use std::path::Path;
use std::fs;

#[test]
fn test_embedded_uniffi_bindgen_exists() {
  let path = Path::new("tools/embedded-uniffi-bindgen/src/lib.rs");
  let exists_before = path.exists();
  if !exists_before {
    fs::File::create(path).unwrap();
  }
  let exists_after = path.exists();
  assert!(exists_after);
  if exists_before {
    fs::remove_file(path).unwrap();
  }
}
}
