# GitHub Pull Request 1394

[[pull request]](https://github.com/mozilla/grcov/pull/1394)
[[linked issue]](https://github.com/mozilla/grcov/issues/1116)

Hi! 🤖 The test below is automatically generated and could serve as a regression test for this PR because it:

- passes on the PR,
- fails in the codebase before the PR, and
- increases line coverage from 92.06% to 94.10%.

```rust
use std::path::PathBuf;
use std::fs::File;
use std::io::Write;
use tempfile::tempdir;

#[test]
fn test_llvm_profiles_to_lcov_with_threads() {
    let tmp_dir = tempdir().unwrap();
    let tmp_path = tmp_dir.path();

    let profdata_path = tmp_path.join("grcov.profdata");
    let binary_path = tmp_path.join("binary");
    let profile_path = tmp_path.join("default.profraw");

    let mut binary_file = File::create(&binary_path).unwrap();
    writeln!(binary_file, "binary content").unwrap();

    let mut profile_file = File::create(&profile_path).unwrap();
    writeln!(profile_file, "profile content").unwrap();

    let result = llvm_profiles_to_lcov(
        &[profile_path],
        &binary_path,
        tmp_path,
        4, // Using 4 threads
    );

    assert!(result.is_err(), "Expected error due to invalid profile data");
}
```

If you find this regression test useful, feel free to insert it to your test suite.
Our automated pipeline inserted the test at the end of the `src/llvm_tools.rs` file before running it.

The test failed on the pre-PR codebase with the following message (to improve clarity, only errors are included).

```text
error[E0061]: this function takes 3 arguments but 4 arguments were supplied
   --> src/llvm_tools.rs:461:22
    |
461 |         let result = llvm_profiles_to_lcov(
    |                      ^^^^^^^^^^^^^^^^^^^^^
...
465 |             4, // Using 4 threads
    |             - unexpected argument #4 of type `{integer}`
    |
note: function defined here
   --> src/llvm_tools.rs:80:8
    |
80  | pub fn llvm_profiles_to_lcov(
    |        ^^^^^^^^^^^^^^^^^^^^^
help: remove the extra argument
    |
464 -             tmp_path,
465 -             4, // Using 4 threads
464 +             tmp_path, // Using 4 threads
    |

For more information about this error, try `rustc --explain E0061`.
error: could not compile `grcov` (lib test) due to 1 previous error
warning: build failed, waiting for other jobs to finish...
```

This is part of our research at the [ZEST](https://www.ifi.uzh.ch/en/zest.html) group of University of Zurich in collaboration with [Mozilla](https://www.mozilla.org).
Looking forward to see what you think of the test. If you find it useful, we can open a PR. Thanks for your time.

<details> <summary>Click to see the test patch.</summary>

```diff
diff --git a/src/llvm_tools.rs b/src/llvm_tools.rs
index af3dcd1..ab0e6c6 100644
--- a/src/llvm_tools.rs
+++ b/src/llvm_tools.rs
@@ -198,6 +198,11 @@ mod tests {
     use tempfile::TempDir;
     use walkdir::WalkDir;

+    use std::path::PathBuf;
+    use std::fs::File;
+    use std::io::Write;
+    use tempfile::tempdir;
+
     const FIXTURES_BASE: &str = "tests/rust/";

     fn get_binary_path(name: &str) -> String {
@@ -445,4 +450,29 @@ mod tests {
             "Missing source file declaration (SF) in lcov report",
         );
     }
-}
+
+    #[test]
+    fn test_llvm_profiles_to_lcov_with_threads() {
+        let tmp_dir = tempdir().unwrap();
+        let tmp_path = tmp_dir.path();
+
+        let profdata_path = tmp_path.join("grcov.profdata");
+        let binary_path = tmp_path.join("binary");
+        let profile_path = tmp_path.join("default.profraw");
+
+        let mut binary_file = File::create(&binary_path).unwrap();
+        writeln!(binary_file, "binary content").unwrap();
+
+        let mut profile_file = File::create(&profile_path).unwrap();
+        writeln!(profile_file, "profile content").unwrap();
+
+        let result = llvm_profiles_to_lcov(
+            &[profile_path],
+            &binary_path,
+            tmp_path,
+            4, // Using 4 threads
+        );
+
+        assert!(result.is_err(), "Expected error due to invalid profile data");
+    }
+}
```

</details>
