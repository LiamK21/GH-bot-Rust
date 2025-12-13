# GitHub Pull Request 3212

[[pull request]](https://github.com/mozilla/glean/pull/3212)
[[linked issue]](https://bugzilla.mozilla.org/show_bug.cgi?id=1899618)

Hi! 🤖 The test below is automatically generated and could serve as a regression test for this PR because it:

- passes on the PR,
- fails in the codebase before the PR, and
- increases line coverage from 0.00% to 92.86%.

```rust
use std::thread;
use std::io;
use super::spawn;
use std::result::Result;

#[test]
fn test_thread_spawn() {
  let handle: Result<std::thread::JoinHandle<()>, std::io::Error> = spawn("test_thread", || {
    assert_eq!("test_thread", std::thread::current().name().unwrap());
  });
  match handle {
    Ok(handle) => {
      let result = handle.join();
      assert!(result.is_ok());
    },
    Err(e) => {
      assert!(false, "Error spawning thread: {}", e);
    }
  }
}
```

If you find this regression test useful, feel free to insert it to your test suite.
Our automated pipeline inserted the test at the end of the `glean-core/src/thread.rs` file before running it.

The test failed on the pre-PR codebase with the following message (to improve clarity, only errors are included).

```text
Empty stdout because file did not exist in pre-PR codebase
```

This is part of our research at the [ZEST](https://www.ifi.uzh.ch/en/zest.html) group of University of Zurich in collaboration with [Mozilla](https://www.mozilla.org).
Looking forward to see what you think of the test. If you find it useful, we can open a PR. Thanks for your time.

<details> <summary>Click to see the test patch.</summary>

```diff
diff --git a/glean-core/src/thread.rs b/glean-core/src/thread.rs
index 316a62f..d67865c 100644
--- a/glean-core/src/thread.rs
+++ b/glean-core/src/thread.rs
@@ -49,3 +49,27 @@ where
             res
         })
 }
+
+#[cfg(test)]
+mod tests {
+use std::thread;
+use std::io;
+use super::spawn;
+use std::result::Result;
+
+#[test]
+fn test_thread_spawn() {
+  let handle: Result<std::thread::JoinHandle<()>, std::io::Error> = spawn("test_thread", || {
+    assert_eq!("test_thread", std::thread::current().name().unwrap());
+  });
+  match handle {
+    Ok(handle) => {
+      let result = handle.join();
+      assert!(result.is_ok());
+    },
+    Err(e) => {
+      assert!(false, "Error spawning thread: {}", e);
+    }
+  }
+}
+}
```

</details>
