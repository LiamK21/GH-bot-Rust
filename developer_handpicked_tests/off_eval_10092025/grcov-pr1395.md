## GitHub Pull Request 1395
[[pull request]](https://github.com/mozilla/grcov/pull/1395)
[[linked issue]](https://github.com/mozilla/grcov/issues/1343)

The test below is automatically generated and could serve as a regression test for this PR because it:
- passes in the post-PR codebase, and
- fails in the pre-PR codebase.

```rust
use super::HtmlGlobalStats;

#[test]
fn test_list_includes_subdirectories() {
    let global_json = r#"
    {
        "dirs": {
            "": {
                "files": {
                    "main.rs": {
                        "stats": {"total_lines": 10, "covered_lines": 5, "total_funs": 1, "covered_funs": 1, "total_branches": 2, "covered_branches": 1},
                        "abs_prefix": null
                    }
                },
                "stats": {"total_lines": 10, "covered_lines": 5, "total_funs": 1, "covered_funs": 1, "total_branches": 2, "covered_branches": 1},
                "abs_prefix": null
            },
            "module": {
                "files": {
                    "mod.rs": {
                        "stats": {"total_lines": 20, "covered_lines": 15, "total_funs": 2, "covered_funs": 2, "total_branches": 4, "covered_branches": 3},
                        "abs_prefix": null
                    }
                },
                "stats": {"total_lines": 20, "covered_lines": 15, "total_funs": 2, "covered_funs": 2, "total_branches": 4, "covered_branches": 3},
                "abs_prefix": null
            }
        },
        "stats": {"total_lines": 30, "covered_lines": 20, "total_funs": 3, "covered_funs": 3, "total_branches": 6, "covered_branches": 4},
        "abs_prefix": null
    }
    "#;

    let global: HtmlGlobalStats = serde_json::from_str(global_json).unwrap();

    let root_items = global.list("".to_string());
    assert_eq!(root_items.len(), 2);
    assert!(root_items.contains_key("main.rs"));
    assert!(root_items.contains_key("module"));

    match root_items.get("module").unwrap() {
        HtmlItemStats::Directory(_) => {}
        HtmlItemStats::File(_) => panic!("module should be a directory"),
    }
}
```

Our automated pipeline inserted the test at the end of the `src/defs.rs` file before running it.
The test failed on the pre-PR codebase with the following message (to improve clarity, only errors are included).

```text
error[E0599]: no method named `list` found for struct `defs::HtmlGlobalStats` in the current scope
   --> src/defs.rs:196:29
    |
119 | pub struct HtmlGlobalStats {
    | -------------------------- method `list` not found for this struct
...
196 |     let root_items = global.list("".to_string());
    |                             ^^^^ method not found in `defs::HtmlGlobalStats`

error[E0277]: the trait bound `defs::HtmlGlobalStats: Deserialize<'_>` is not satisfied
    --> src/defs.rs:194:35
     |
194  |     let global: HtmlGlobalStats = serde_json::from_str(global_json).unwrap();
     |                                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ the trait `Deserialize<'_>` is not implemented for `defs::HtmlGlobalStats`
     |
     = note: for local types consider adding `#[derive(serde::Deserialize)]` to your `defs::HtmlGlobalStats` type
     = note: for types from other crates check whether the crate offers a `serde` feature flag
     = help: the following other types implement trait `Deserialize<'de>`:
               &'a [u8]
               &'a std::path::Path
               &'a str
               ()
               (T,)
               (T0, T1)
               (T0, T1, T2)
               (T0, T1, T2, T3)
             and 152 others
note: required by a bound in `serde_json::from_str`
    --> /usr/local/cargo/registry/src/index.crates.io-1949cf8c6b5b557f/serde_json-1.0.142/src/de.rs:2699:8
     |
2697 | pub fn from_str<'a, T>(s: &'a str) -> Result<T>
     |        -------- required by a bound in this function
2698 | where
2699 |     T: de::Deserialize<'a>,
     |        ^^^^^^^^^^^^^^^^^^^ required by this bound in `from_str`

error[E0433]: failed to resolve: use of undeclared type `HtmlItemStats`
   --> src/defs.rs:202:9
    |
202 |         HtmlItemStats::Directory(_) => {}
    |         ^^^^^^^^^^^^^ use of undeclared type `HtmlItemStats`

error[E0433]: failed to resolve: use of undeclared type `HtmlItemStats`
   --> src/defs.rs:203:9
    |
203 |         HtmlItemStats::File(_) => panic!("module should be a directory"),
    |         ^^^^^^^^^^^^^ use of undeclared type `HtmlItemStats`

Some errors have detailed explanations: E0277, E0433, E0599.
For more information about an error, try `rustc --explain E0277`.
error: could not compile `grcov` (lib test) due to 4 previous errors
warning: build failed, waiting for other jobs to finish...
```

This is part of our research at the [ZEST](https://www.ifi.uzh.ch/en/zest.html) group of University of Zurich in collaboration with [Mozilla](https://www.mozilla.org/). \
Looking forward to see what you think of the test. If you find it useful, we can open a PR. Thanks for your time.

<details> <summary>Click to see the test patch.</summary>
Note: If you wish to appply this patch, check out commmit e0d7c9fb117b694f0dfcf5fa16b85a60fc472c43 at forked repository linw1995:master

```diff
diff --git a/src/defs.rs b/src/defs.rs
index b933ba7..e659a2a 100644
--- a/src/defs.rs
+++ b/src/defs.rs
@@ -214,6 +214,8 @@ pub struct JacocoReport {
 mod tests {
     use super::*;
 
+
+
     #[test]
     fn test_html_global_stats_list() {
         let global_json = r#"
@@ -287,4 +289,48 @@ mod tests {
         assert_eq!(utils_items.len(), 1);
         assert!(utils_items.contains_key("mod.rs"));
     }
-}
+
+    #[test]
+    fn test_list_includes_subdirectories() {
+        let global_json = r#"
+        {
+            "dirs": {
+                "": {
+                    "files": {
+                        "main.rs": {
+                            "stats": {"total_lines": 10, "covered_lines": 5, "total_funs": 1, "covered_funs": 1, "total_branches": 2, "covered_branches": 1},
+                            "abs_prefix": null
+                        }
+                    },
+                    "stats": {"total_lines": 10, "covered_lines": 5, "total_funs": 1, "covered_funs": 1, "total_branches": 2, "covered_branches": 1},
+                    "abs_prefix": null
+                },
+                "module": {
+                    "files": {
+                        "mod.rs": {
+                            "stats": {"total_lines": 20, "covered_lines": 15, "total_funs": 2, "covered_funs": 2, "total_branches": 4, "covered_branches": 3},
+                            "abs_prefix": null
+                        }
+                    },
+                    "stats": {"total_lines": 20, "covered_lines": 15, "total_funs": 2, "covered_funs": 2, "total_branches": 4, "covered_branches": 3},
+                    "abs_prefix": null
+                }
+            },
+            "stats": {"total_lines": 30, "covered_lines": 20, "total_funs": 3, "covered_funs": 3, "total_branches": 6, "covered_branches": 4},
+            "abs_prefix": null
+        }
+        "#;
+
+        let global: HtmlGlobalStats = serde_json::from_str(global_json).unwrap();
+
+        let root_items = global.list("".to_string());
+        assert_eq!(root_items.len(), 2);
+        assert!(root_items.contains_key("main.rs"));
+        assert!(root_items.contains_key("module"));
+
+        match root_items.get("module").unwrap() {
+            HtmlItemStats::Directory(_) => {}
+            HtmlItemStats::File(_) => panic!("module should be a directory"),
+        }
+    }
+}

```

</details>
