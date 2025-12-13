## GitHub Pull Request 736

[[pull request]](https://github.com/mozilla/rust-code-analysis/pull/736)
[[linked issue]](https://github.com/mozilla/rust-code-analysis/issues/409)

Hi! 🤖 The test below is automatically generated and could serve as a regression test for this PR because it:

- passes on the PR,
- fails in the codebase before the PR, and
- increases line coverage from 82.71% to 83.63%.

```rust
#[test]
fn test_functions_and_closures_average() {
    let mut stats = Stats::default();
    stats.space_count = 4;
    stats.functions_sum = 3;
    stats.closures_sum = 1;

    let expected_functions_average = 0.75;
    let expected_closures_average = 0.25;
    let expected_average = 1.0;

    let actual_functions_average = stats.functions_average();
    let actual_closures_average = stats.closures_average();
    let actual_average = stats.average();

    assert_eq!(expected_functions_average, actual_functions_average);
    assert_eq!(expected_closures_average, actual_closures_average);
    assert_eq!(expected_average, actual_average);
}
```

If you find this regression test useful, feel free to insert it to your test suite.
Our automated pipeline inserted the test at the end of the `src/metrics/nom.rs` file before running it.

The test failed on the pre-PR codebase with the following message (to improve clarity, only errors are included).

```text
error[E0609]: no field `space_count` on type `metrics::nom::Stats`
   --> src/metrics/nom.rs:520:15
    |
520 |         stats.space_count = 4;
    |               ^^^^^^^^^^^ unknown field
    |
    = note: available fields are: `functions`, `closures`, `functions_sum`, `closures_sum`, `functions_min` ... and 3 others

error[E0599]: no method named `functions_average` found for struct `metrics::nom::Stats` in the current scope
   --> src/metrics/nom.rs:528:46
    |
11  | pub struct Stats {
    | ---------------- method `functions_average` not found for this struct
...
528 |         let actual_functions_average = stats.functions_average();
    |                                              ^^^^^^^^^^^^^^^^^
    |
help: there is a method `functions` with a similar name
    |
528 -         let actual_functions_average = stats.functions_average();
528 +         let actual_functions_average = stats.functions();
    |

error[E0599]: no method named `closures_average` found for struct `metrics::nom::Stats` in the current scope
   --> src/metrics/nom.rs:529:45
    |
11  | pub struct Stats {
    | ---------------- method `closures_average` not found for this struct
...
529 |         let actual_closures_average = stats.closures_average();
    |                                             ^^^^^^^^^^^^^^^^
    |
help: there is a method `closures` with a similar name
    |
529 -         let actual_closures_average = stats.closures_average();
529 +         let actual_closures_average = stats.closures();
    |

error[E0599]: no method named `average` found for struct `metrics::nom::Stats` in the current scope
   --> src/metrics/nom.rs:530:36
    |
11  | pub struct Stats {
    | ---------------- method `average` not found for this struct
...
530 |         let actual_average = stats.average();
    |                                    ^^^^^^^
    |
help: there is a method `merge` with a similar name, but with different arguments
   --> src/metrics/nom.rs:76:5
    |
76  |     pub fn merge(&mut self, other: &Stats) {
    |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

. . .

Some errors have detailed explanations: E0599, E0609.
For more information about an error, try `rustc --explain E0599`.
error: could not compile `rust-code-analysis` (lib test) due to 4 previous errors
warning: build failed, waiting for other jobs to finish...
warning: `rust-code-analysis` (lib) generated 12 warnings
```

This is part of our research at the [ZEST](https://www.ifi.uzh.ch/en/zest.html) group of University of Zurich in collaboration with [Mozilla](https://www.mozilla.org).
Looking forward to see what you think of the test. If you find it useful, we can open a PR. Thanks for your time.

<details> <summary>Click to see the test patch.</summary>

```diff
diff --git a/src/metrics/nom.rs b/src/metrics/nom.rs
index 7046ce1..cbd6a54 100644
--- a/src/metrics/nom.rs
+++ b/src/metrics/nom.rs
@@ -211,6 +211,8 @@ mod tests {

     use super::*;

+
+
     #[test]
     fn python_nom() {
         check_metrics!(
@@ -616,4 +618,24 @@ mod tests {
             ]
         );
     }
-}
+
+    #[test]
+    fn test_functions_and_closures_average() {
+        let mut stats = Stats::default();
+        stats.space_count = 4;
+        stats.functions_sum = 3;
+        stats.closures_sum = 1;
+
+        let expected_functions_average = 0.75;
+        let expected_closures_average = 0.25;
+        let expected_average = 1.0;
+
+        let actual_functions_average = stats.functions_average();
+        let actual_closures_average = stats.closures_average();
+        let actual_average = stats.average();
+
+        assert_eq!(expected_functions_average, actual_functions_average);
+        assert_eq!(expected_closures_average, actual_closures_average);
+        assert_eq!(expected_average, actual_average);
+    }
+}
```

</details>
