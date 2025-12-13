## GitHub Pull Request 793
[[pull request]](https://github.com/mozilla/rust-code-analysis/pull/793)
[[linked issue]](https://github.com/mozilla/rust-code-analysis/issues/410)

The test below is automatically generated and could serve as a regression test for this PR because it:
- passes in the post-PR codebase, and
- fails in the pre-PR codebase.

```rust
use super::Stats;
use std::fmt;

#[test]
fn test_loc_min_max() {
  let mut stats = Stats::default();
  stats.sloc.start = 1;
  stats.sloc.end = 10;
  stats.sloc.unit = true;
  stats.ploc.lines.insert(1);
  stats.ploc.lines.insert(2);
  stats.cloc.only_comment_lines = 1;
  stats.cloc.code_comment_lines = 1;
  stats.lloc.logical_lines = 5;
  stats.compute_minmax();
  assert_eq!(stats.sloc_min(), 9.0);
  assert_eq!(stats.sloc_max(), 9.0);
  assert_eq!(stats.ploc_min(), 2.0);
  assert_eq!(stats.ploc_max(), 2.0);
  assert_eq!(stats.cloc_min() as f64, 2.0);
  assert_eq!(stats.cloc_max() as f64, 2.0);
  assert_eq!(stats.lloc_min(), 5.0);
  assert_eq!(stats.lloc_max(), 5.0);
}
```

Our automated pipeline inserted the test at the end of the `src/metrics/loc.rs` file before running it.
The test failed on the pre-PR codebase with the following message (to improve clarity, only errors are included).

```text
error[E0615]: attempted to take value of method `sloc` on type `metrics::loc::Stats`
    --> src/metrics/loc.rs:1437:13
     |
1437 |       stats.sloc.start = 1;
     |             ^^^^ method, not a field
     |
     = help: methods are immutable and cannot be assigned to

error[E0615]: attempted to take value of method `sloc` on type `metrics::loc::Stats`
    --> src/metrics/loc.rs:1438:13
     |
1438 |       stats.sloc.end = 10;
     |             ^^^^ method, not a field
     |
     = help: methods are immutable and cannot be assigned to

error[E0615]: attempted to take value of method `sloc` on type `metrics::loc::Stats`
    --> src/metrics/loc.rs:1439:13
     |
1439 |       stats.sloc.unit = true;
     |             ^^^^ method, not a field
     |
     = help: methods are immutable and cannot be assigned to

error[E0615]: attempted to take value of method `ploc` on type `metrics::loc::Stats`
    --> src/metrics/loc.rs:1440:13
     |
1440 |       stats.ploc.lines.insert(1);
     |             ^^^^ method, not a field
     |

error[E0615]: attempted to take value of method `ploc` on type `metrics::loc::Stats`
    --> src/metrics/loc.rs:1441:13
     |
1441 |       stats.ploc.lines.insert(2);
     |             ^^^^ method, not a field
     |
help: use parentheses to call the method
     |
1441 |       stats.ploc().lines.insert(2);
     |                 ++

error[E0615]: attempted to take value of method `cloc` on type `metrics::loc::Stats`
    --> src/metrics/loc.rs:1442:13
     |
1442 |       stats.cloc.only_comment_lines = 1;
     |             ^^^^ method, not a field
     |
     = help: methods are immutable and cannot be assigned to

error[E0615]: attempted to take value of method `cloc` on type `metrics::loc::Stats`
    --> src/metrics/loc.rs:1443:13
     |
1443 |       stats.cloc.code_comment_lines = 1;
     |             ^^^^ method, not a field
     |
     = help: methods are immutable and cannot be assigned to

error[E0615]: attempted to take value of method `lloc` on type `metrics::loc::Stats`
    --> src/metrics/loc.rs:1444:13
     |
1444 |       stats.lloc.logical_lines = 5;
     |             ^^^^ method, not a field
     |
     = help: methods are immutable and cannot be assigned to

error[E0599]: no method named `compute_minmax` found for struct `metrics::loc::Stats` in the current scope
    --> src/metrics/loc.rs:1445:13
     |
11   | pub struct Stats {
     | ---------------- method `compute_minmax` not found for this struct
...
1445 |       stats.compute_minmax();
     |             ^^^^^^^^^^^^^^ method not found in `metrics::loc::Stats`

error[E0599]: no method named `sloc_min` found for struct `metrics::loc::Stats` in the current scope
    --> src/metrics/loc.rs:1446:24
     |
11   | pub struct Stats {
     | ---------------- method `sloc_min` not found for this struct
...
1446 |       assert_eq!(stats.sloc_min(), 9.0);
     |                        ^^^^^^^^
     |

error[E0599]: no method named `sloc_max` found for struct `metrics::loc::Stats` in the current scope
    --> src/metrics/loc.rs:1447:24
     |
11   | pub struct Stats {
     | ---------------- method `sloc_max` not found for this struct
...
1447 |       assert_eq!(stats.sloc_max(), 9.0);
     |                        ^^^^^^^^
     |
help: there is a method `sloc` with a similar name
     |
1447 -       assert_eq!(stats.sloc_max(), 9.0);
1447 +       assert_eq!(stats.sloc(), 9.0);
     |

error[E0599]: no method named `ploc_min` found for struct `metrics::loc::Stats` in the current scope
    --> src/metrics/loc.rs:1448:24
     |
11   | pub struct Stats {
     | ---------------- method `ploc_min` not found for this struct
...
1448 |       assert_eq!(stats.ploc_min(), 2.0);
     |                        ^^^^^^^^
     |

error[E0599]: no method named `ploc_max` found for struct `metrics::loc::Stats` in the current scope
    --> src/metrics/loc.rs:1449:24
     |
11   | pub struct Stats {
     | ---------------- method `ploc_max` not found for this struct
...
1449 |       assert_eq!(stats.ploc_max(), 2.0);
     |                        ^^^^^^^^
     |
help: there is a method `ploc` with a similar name
     |
1449 -       assert_eq!(stats.ploc_max(), 2.0);
1449 +       assert_eq!(stats.ploc(), 2.0);
     |

error[E0599]: no method named `cloc_min` found for struct `metrics::loc::Stats` in the current scope
    --> src/metrics/loc.rs:1450:24
     |
11   | pub struct Stats {
     | ---------------- method `cloc_min` not found for this struct
...
1450 |       assert_eq!(stats.cloc_min() as f64, 2.0);
     |                        ^^^^^^^^
     |

error[E0599]: no method named `cloc_max` found for struct `metrics::loc::Stats` in the current scope
    --> src/metrics/loc.rs:1451:24
     |
11   | pub struct Stats {
     | ---------------- method `cloc_max` not found for this struct
...
1451 |       assert_eq!(stats.cloc_max() as f64, 2.0);
     |                        ^^^^^^^^
     |
help: there is a method `cloc` with a similar name
     |
1451 -       assert_eq!(stats.cloc_max() as f64, 2.0);
1451 +       assert_eq!(stats.cloc() as f64, 2.0);
     |

error[E0599]: no method named `lloc_min` found for struct `metrics::loc::Stats` in the current scope
    --> src/metrics/loc.rs:1452:24
     |
11   | pub struct Stats {
     | ---------------- method `lloc_min` not found for this struct
...
1452 |       assert_eq!(stats.lloc_min(), 5.0);
     |                        ^^^^^^^^
     |
help: there is a method `lloc` with a similar name
     |
1452 -       assert_eq!(stats.lloc_min(), 5.0);
1452 +       assert_eq!(stats.lloc(), 5.0);
     |

error[E0599]: no method named `lloc_max` found for struct `metrics::loc::Stats` in the current scope
    --> src/metrics/loc.rs:1453:24
     |
11   | pub struct Stats {
     | ---------------- method `lloc_max` not found for this struct
...
1453 |       assert_eq!(stats.lloc_max(), 5.0);
     |                        ^^^^^^^^
     |


warning: `rust-code-analysis` (lib) generated 12 warnings
Some errors have detailed explanations: E0599, E0615.
For more information about an error, try `rustc --explain E0599`.
warning: `rust-code-analysis` (lib test) generated 1 warning
error: could not compile `rust-code-analysis` (lib test) due to 17 previous errors; 1 warning emitted
warning: build failed, waiting for other jobs to finish...
```

This is part of our research at the [ZEST](https://www.ifi.uzh.ch/en/zest.html) group of University of Zurich in collaboration with [Mozilla](https://www.mozilla.org/). \
Looking forward to see what you think of the test. If you find it useful, we can open a PR. Thanks for your time.

<details> <summary>Click to see the test patch.</summary>
Note: If you wish to appply this patch, check out commmit 630673416a583374933eacd9aeb4a15ef99a1d36 at forked repositorySoftengPoliTo:min-max-metrics

```diff
diff --git a/src/metrics/loc.rs b/src/metrics/loc.rs
index 9315d05..f3d5ef6 100644
--- a/src/metrics/loc.rs
+++ b/src/metrics/loc.rs
@@ -510,6 +510,8 @@ mod tests {
 
     use super::*;
 
+    use std::fmt;
+
     #[test]
     fn python_sloc() {
         check_metrics!(
@@ -1428,4 +1430,26 @@ mod tests {
             ]
         );
     }
-}
+
+    #[test]
+    fn test_loc_min_max() {
+      let mut stats = Stats::default();
+      stats.sloc.start = 1;
+      stats.sloc.end = 10;
+      stats.sloc.unit = true;
+      stats.ploc.lines.insert(1);
+      stats.ploc.lines.insert(2);
+      stats.cloc.only_comment_lines = 1;
+      stats.cloc.code_comment_lines = 1;
+      stats.lloc.logical_lines = 5;
+      stats.compute_minmax();
+      assert_eq!(stats.sloc_min(), 9.0);
+      assert_eq!(stats.sloc_max(), 9.0);
+      assert_eq!(stats.ploc_min(), 2.0);
+      assert_eq!(stats.ploc_max(), 2.0);
+      assert_eq!(stats.cloc_min() as f64, 2.0);
+      assert_eq!(stats.cloc_max() as f64, 2.0);
+      assert_eq!(stats.lloc_min(), 5.0);
+      assert_eq!(stats.lloc_max(), 5.0);
+    }
+}

```

</details>
