#src/cobertura.rs
#[cfg(test)]
mod tests {
use super::output_cobertura;
use std::io::Write;
use tempfile::tempdir;
use std::fs::File;
use std::io::Read;
use std::path::PathBuf;

#[test]
fn test_cobertura_output() {
  let tmp_dir = tempfile::tempdir().expect("Failed to create temporary directory");
  let file_name = "test_cobertura.xml";
  let file_path = tmp_dir.path().join(&file_name);

  let results = vec![(
    PathBuf::from("main.rs"),
    PathBuf::from("main.rs"),
    super::CovResult {
      lines: [(1, 1), (2, 1), (3, 2), (4, 1), (5, 0), (6, 0), (8, 1), (9, 1)],
      branches: {
        let mut map = std::collections::BTreeMap::new();
        map.insert(3, vec![true, false]);
        map
      },
      functions: {
        let mut map = std::collections::FxHashMap::default();
        map.insert(
          "_ZN8cov_test4main17h7eb435a3fb3e6f20E".to_string(),
          super::Function {
            start: 1,
            executed: true,
          },
        );
        map
      },
    },
  )];

  let results = Box::new(results.into_iter());
  output_cobertura(results, Some(file_path.to_str().unwrap()), true);

  let mut file = File::open(file_path).expect("Failed to open file");
  let mut contents = String::new();
  file.read_to_string(&mut contents).expect("Failed to read file");

  assert!(contents.contains(r#"package name="main.rs""#));
  assert!(contents.contains(r#"class name="main" filename="main.rs""#));
  assert!(contents.contains(r#"method name="cov_test::main""#));
  assert!(contents.contains(r#"line number="1" hits="1">"#));
  assert!(contents.contains(r#"line number="3" hits="2" branch="true""#));
  assert!(contents.contains(r#"<condition number="0" type="jump" coverage="1"/>"#));
}
}
