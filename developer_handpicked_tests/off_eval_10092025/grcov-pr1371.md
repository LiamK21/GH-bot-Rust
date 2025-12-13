## GitHub Pull Request 1371

[[pull request]](https://github.com/mozilla/grcov/pull/1371)
[[linked issue]](https://github.com/mozilla/grcov/issues/1242)

The test below is automatically generated and could serve as a regression test for this PR because it:

- passes in the post-PR codebase, and
- fails in the pre-PR codebase.

```rust
use super::parse_lcov;
use std::fs::File;
use std::io::Read;
use std::path::Path;

#[test]
fn test_lcov_parser_ignore_parsing_error() {
  let mut f = File::open("./test/invalid_DA_record.info").expect("Failed to open lcov file");
  let mut buf = Vec::new();
  f.read_to_end(&mut buf).unwrap();
  let result_before_patch = parse_lcov(buf.clone(), true, false);
  assert!(result_before_patch.is_err());
  let result_after_patch = parse_lcov(buf, true, true);
  assert!(result_after_patch.is_ok());
  let results = result_after_patch.unwrap();
  assert!(results.len() > 0);
}
```

Our automated pipeline inserted the test at the end of the `src/parser.rs` file before running it.
The test failed on the pre-PR codebase with the following message (to improve clarity, only errors are included).

```text
error[E0061]: this function takes 2 arguments but 3 arguments were supplied
    --> src/parser.rs:2791:33
     |
2791 |       let result_before_patch = parse_lcov(buf.clone(), true, false);
     |                                 ^^^^^^^^^^                    ----- unexpected argument #3 of type `bool`
     |
note: function defined here
    --> src/parser.rs:143:8
     |
143  | pub fn parse_lcov(
     |        ^^^^^^^^^^

error[E0061]: this function takes 2 arguments but 3 arguments were supplied
    --> src/parser.rs:2793:32
     |
2793 |       let result_after_patch = parse_lcov(buf, true, true);
     |                                ^^^^^^^^^^            ---- unexpected argument #3 of type `bool`
     |
note: function defined here
    --> src/parser.rs:143:8
     |
143  | pub fn parse_lcov(
     |        ^^^^^^^^^^

For more information about this error, try `rustc --explain E0061`.
error: could not compile `grcov` (lib test) due to 2 previous errors
warning: build failed, waiting for other jobs to finish...
```

This is part of our research at the [ZEST](https://www.ifi.uzh.ch/en/zest.html) group of University of Zurich in collaboration with [Mozilla](https://www.mozilla.org/).
Looking forward to see what you think of the test. If you find it useful, we can open a PR. Thanks for your time.

<details> <summary>Click to see the test patch.</summary>
Note: If you wish to appply this patch, check out commmit 6758022cfc1687560b33fc080313a8d2191f011e at forked repository a-lubert:feat/ignore-parsing-error

```diff
diff --git a/src/parser.rs b/src/parser.rs
index 11297d8..07e5ad3 100644
--- a/src/parser.rs
+++ b/src/parser.rs
@@ -931,6 +931,10 @@ pub fn parse_gocov<T: Read>(
 mod tests {
     use super::*;

+    use std::fs::File;
+    use std::io::Read;
+    use std::path::Path;
+
     #[test]
     fn test_remove_newline() {
         let mut l = "Marco".as_bytes().to_vec();
@@ -2778,4 +2782,17 @@ TN:http_3a_2f_2fweb_2dplatform_2etest_3a8000_2freferrer_2dpolicy_2fgen_2fsrcdoc_
         let results = parse_gocov(&mut file).unwrap();
         assert_eq!(results, expected);
     }
-}
+
+    #[test]
+    fn test_lcov_parser_ignore_parsing_error() {
+      let mut f = File::open("./test/invalid_DA_record.info").expect("Failed to open lcov file");
+      let mut buf = Vec::new();
+      f.read_to_end(&mut buf).unwrap();
+      let result_before_patch = parse_lcov(buf.clone(), true, false);
+      assert!(result_before_patch.is_err());
+      let result_after_patch = parse_lcov(buf, true, true);
+      assert!(result_after_patch.is_ok());
+      let results = result_after_patch.unwrap();
+      assert!(results.len() > 0);
+    }
+}

```

</details>
