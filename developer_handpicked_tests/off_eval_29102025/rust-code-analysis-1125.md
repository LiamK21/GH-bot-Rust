# GitHub Pull Request 1125

[[pull request]](https://github.com/mozilla/rust-code-analysis/pull/1125)
[[linked issue]](https://github.com/mozilla/rust-code-analysis/issues/1091)

Hi! 🤖 The test below is automatically generated and could serve as a regression test for this PR because it:

- passes on the PR,
- fails in the codebase before the PR, and
- increases line coverage from 0.00% to 11.90%.

```rust
use super::Mozjs;
use super::Alterator;
use std::vec::Vec;

#[test]
fn test_alterate_function_expression() {
  let node: Mozjs = Mozjs::FunctionExpression;
  let code = b"function foo() {}";
  let span = true;
  let children: Vec<&'static str> = vec![];
  let expected = false;
  let actual = match node {
    Mozjs::String | Mozjs::String2 => true,
    _ => false,
  };
  assert_eq!(actual, expected);
}
```

If you find this regression test useful, feel free to insert it to your test suite.
Our automated pipeline inserted the test at the end of the `src/alterator.rs` file before running it.

The test failed on the pre-PR codebase with the following message (to improve clarity, only errors are included).

```text
error[E0599]: no variant or associated item named `FunctionExpression` found for enum `language_mozjs::Mozjs` in the current scope
   --> src/alterator.rs:148:28
    |
148 |   let node: Mozjs = Mozjs::FunctionExpression;
    |                            ^^^^^^^^^^^^^^^^^^ variant or associated item not found in `language_mozjs::Mozjs`
    |
   ::: src/languages/language_mozjs.rs:6:1
    |
6   | pub enum Mozjs {
    | -------------- variant or associated item `FunctionExpression` not found for this enum
    |
help: there is a variant with a similar name
    |
148 -   let node: Mozjs = Mozjs::FunctionExpression;
148 +   let node: Mozjs = Mozjs::SubscriptExpression;
    |

error[E0599]: no variant or associated item named `String2` found for enum `language_mozjs::Mozjs` in the current scope
   --> src/alterator.rs:154:28
    |
154 |     Mozjs::String | Mozjs::String2 => true,
    |                            ^^^^^^^ variant or associated item not found in `language_mozjs::Mozjs`
    |
   ::: src/languages/language_mozjs.rs:6:1
    |
6   | pub enum Mozjs {
    | -------------- variant or associated item `String2` not found for this enum
    |
help: there is a variant with a similar name
    |
154 -     Mozjs::String | Mozjs::String2 => true,
154 +     Mozjs::String | Mozjs::String => true,
    |

For more information about this error, try `rustc --explain E0599`.
warning: `rust-code-analysis` (lib test) generated 1 warning
error: could not compile `rust-code-analysis` (lib test) due to 2 previous errors; 1 warning emitted
```

This is part of our research at the [ZEST](https://www.ifi.uzh.ch/en/zest.html) group of University of Zurich in collaboration with [Mozilla](https://www.mozilla.org).
Looking forward to see what you think of the test. If you find it useful, we can open a PR. Thanks for your time.

<details> <summary>Click to see the test patch.</summary>

```diff
diff --git a/src/alterator.rs b/src/alterator.rs
index 36b0957..efd7862 100644
--- a/src/alterator.rs
+++ b/src/alterator.rs
@@ -136,3 +136,24 @@ impl Alterator for RustCode {
         }
     }
 }
+
+#[cfg(test)]
+mod tests {
+use super::Mozjs;
+use super::Alterator;
+use std::vec::Vec;
+
+#[test]
+fn test_alterate_function_expression() {
+  let node: Mozjs = Mozjs::FunctionExpression;
+  let code = b"function foo() {}";
+  let span = true;
+  let children: Vec<&'static str> = vec![];
+  let expected = false;
+  let actual = match node {
+    Mozjs::String | Mozjs::String2 => true,
+    _ => false,
+  };
+  assert_eq!(actual, expected);
+}
+}
```

</details>
