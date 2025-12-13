## GitHub Pull Request 3212

[[pull request]](https://github.com/mozilla/glean/pull/3212)
[[linked issue]](https://bugzilla.mozilla.org/show_bug.cgi?id=1899618)

Hi! 🤖 The test below is automatically generated and could serve as a regression test for this PR because it:

- passes on the PR,
- fails in the codebase before the PR, and
- increases line coverage from 0.00% to 100.00%.

```rust
use super::spawn;
use std::sync::{Arc, Mutex};
use std::thread;

#[test]
fn test_thread_registration_and_unregistration() {
    let counter = Arc::new(Mutex::new(0));
    let counter_clone = Arc::clone(&counter);

    let handle = spawn("test_thread", move || {
        let mut num = counter_clone.lock().unwrap();
        *num += 1;
    }).expect("Failed to spawn thread");

    handle.join().expect("Thread panicked");

    let result = *counter.lock().unwrap();
    assert_eq!(result, 1);
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
index 316a62f..b1a1288 100644
--- a/glean-core/src/thread.rs
+++ b/glean-core/src/thread.rs
@@ -49,3 +49,26 @@ where
             res
         })
 }
+
+#[cfg(test)]
+mod tests {
+use super::spawn;
+use std::sync::{Arc, Mutex};
+use std::thread;
+
+#[test]
+fn test_thread_registration_and_unregistration() {
+    let counter = Arc::new(Mutex::new(0));
+    let counter_clone = Arc::clone(&counter);
+
+    let handle = spawn("test_thread", move || {
+        let mut num = counter_clone.lock().unwrap();
+        *num += 1;
+    }).expect("Failed to spawn thread");
+
+    handle.join().expect("Thread panicked");
+
+    let result = *counter.lock().unwrap();
+    assert_eq!(result, 1);
+}
+}
```

</details>
