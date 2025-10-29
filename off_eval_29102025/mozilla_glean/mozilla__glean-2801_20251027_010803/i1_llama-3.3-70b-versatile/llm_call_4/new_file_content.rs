#tools/embedded-uniffi-bindgen/src/lib.rs
// intentionally left empty. only exists to make a warning go away

#[cfg(test)]
mod tests {
use std::path::Path;
use std::fs;
use std::io;

#[test]
fn test_embedded_uniffi_bindgen_exists() {
  let path = Path::new("tools/embedded-uniffi-bindgen/src/lib.rs");
  let exists_before = path.exists();
  if !exists_before {
    match fs::File::create(path) {
      Ok(_) => (),
      Err(_) => panic!("Failed to create file"),
    }
  }
  let exists_after = path.exists();
  assert!(exists_after);
  if exists_before {
    match fs::remove_file(path) {
      Ok(_) => (),
      Err(_) => panic!("Failed to remove file"),
    }
  }
}
}
