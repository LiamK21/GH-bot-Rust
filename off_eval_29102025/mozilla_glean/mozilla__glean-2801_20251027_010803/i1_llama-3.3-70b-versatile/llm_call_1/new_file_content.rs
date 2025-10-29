#tools/embedded-uniffi-bindgen/src/lib.rs
// intentionally left empty. only exists to make a warning go away

#[cfg(test)]
mod tests {
use std::ffi::OsStr;
use std::path::Path;
use std::process::Command;

#[test]
fn test_embedded_uniffi_bindgen_exists() {
  let path = Path::new("tools/embedded-uniffi-bindgen/src/lib.rs");
  let exists = path.exists();
  assert!(exists);
}
}
