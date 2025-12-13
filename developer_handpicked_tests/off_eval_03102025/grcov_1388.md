## GitHub Pull Request 1388

[[pull request]](https://github.com/mozilla/grcov/pull/1388)
[[linked issue]](https://github.com/mozilla/grcov/issues/1386)

Hi! 🤖 The test below is automatically generated and could serve as a regression test for this PR because it:

- passes on the PR,
- fails in the codebase before the PR, and
- increases line coverage from 93.84% to 95.29%.

```rust
#[test]
fn test_is_known_binary() {
    let elf_bytes = [0x7F, b'E', b'L', b'F', 0, 0, 0, 0];
    let pe_bytes = [0x4D, 0x5A, 0, 0, 0, 0, 0, 0, b'B', b'S', b'J', b'B'];
    let macho_bytes = [0xFE, 0xED, 0xFA, 0xCE, 0, 0, 0, 0];
    let coff_bytes = [0x4C, 0x01, 0, 0, 0, 0, 0, 0];
    let wasm_bytes = [0x00, 0x61, 0x73, 0x6D, 0, 0, 0, 0];
    let llvm_bytes = [0x42, 0x43, 0xC0, 0xDE, 0, 0, 0, 0];
    let unknown_bytes = [0x00, 0x00, 0x00, 0x00, 0, 0, 0, 0];

    assert!(is_known_binary(&elf_bytes));
    assert!(is_known_binary(&pe_bytes));
    assert!(is_known_binary(&macho_bytes));
    assert!(is_known_binary(&coff_bytes));
    assert!(is_known_binary(&wasm_bytes));
    assert!(is_known_binary(&llvm_bytes));
    assert!(!is_known_binary(&unknown_bytes));
}
```

If you find this regression test useful, feel free to insert it to your test suite.
Our automated pipeline inserted the test at the end of the `src/file_walker.rs` file before running it.

The test failed on the pre-PR codebase with the following message (to improve clarity, only errors are included).

```text
error[E0425]: cannot find function `is_known_binary` in this scope
--> src/file_walker.rs:744:17
|
744 | assert!(is_known_binary(&elf_bytes));
| ^^^^^^^^^^^^^^^ not found in this scope

error[E0425]: cannot find function `is_known_binary` in this scope
--> src/file_walker.rs:745:17
|
745 | assert!(is_known_binary(&pe_bytes));
| ^^^^^^^^^^^^^^^ not found in this scope

error[E0425]: cannot find function `is_known_binary` in this scope
--> src/file_walker.rs:746:17
|
746 | assert!(is_known_binary(&macho_bytes));
| ^^^^^^^^^^^^^^^ not found in this scope

error[E0425]: cannot find function `is_known_binary` in this scope
--> src/file_walker.rs:747:17
|
747 | assert!(is_known_binary(&coff_bytes));
| ^^^^^^^^^^^^^^^ not found in this scope

error[E0425]: cannot find function `is_known_binary` in this scope
--> src/file_walker.rs:748:17
|
748 | assert!(is_known_binary(&wasm_bytes));
| ^^^^^^^^^^^^^^^ not found in this scope

error[E0425]: cannot find function `is_known_binary` in this scope
--> src/file_walker.rs:749:17
|
749 | assert!(is_known_binary(&llvm_bytes));
| ^^^^^^^^^^^^^^^ not found in this scope

error[E0425]: cannot find function `is_known_binary` in this scope
--> src/file_walker.rs:750:18
|
750 | assert!(!is_known_binary(&unknown_bytes));
| ^^^^^^^^^^^^^^^ not found in this scope

For more information about this error, try `rustc --explain E0425`.
error: could not compile `grcov` (lib test) due to 7 previous errors
warning: build failed, waiting for other jobs to finish...
```

This is part of our research at the [ZEST](https://www.ifi.uzh.ch/en/zest.html) group of University of Zurich in collaboration with [Mozilla](https://www.mozilla.org).
Looking forward to see what you think of the test. If you find it useful, we can open a PR. Thanks for your time.

<details> <summary>Click to see the test patch.</summary>

```diff
diff --git a/src/file_walker.rs b/src/file_walker.rs
index 6f33f1d..7f6ba90 100644
--- a/src/file_walker.rs
+++ b/src/file_walker.rs
@@ -269,6 +269,8 @@ mod tests {
     use std::io::Write;
     use tempfile::tempdir;

+
+
     #[cfg(unix)]
     use std::os::unix::fs as unix_fs;

@@ -787,4 +789,23 @@ mod tests {
             "No duplicate files should be found"
         );
     }
-}
+
+    #[test]
+    fn test_is_known_binary() {
+        let elf_bytes = [0x7F, b'E', b'L', b'F', 0, 0, 0, 0];
+        let pe_bytes = [0x4D, 0x5A, 0, 0, 0, 0, 0, 0, b'B', b'S', b'J', b'B'];
+        let macho_bytes = [0xFE, 0xED, 0xFA, 0xCE, 0, 0, 0, 0];
+        let coff_bytes = [0x4C, 0x01, 0, 0, 0, 0, 0, 0];
+        let wasm_bytes = [0x00, 0x61, 0x73, 0x6D, 0, 0, 0, 0];
+        let llvm_bytes = [0x42, 0x43, 0xC0, 0xDE, 0, 0, 0, 0];
+        let unknown_bytes = [0x00, 0x00, 0x00, 0x00, 0, 0, 0, 0];
+
+        assert!(is_known_binary(&elf_bytes));
+        assert!(is_known_binary(&pe_bytes));
+        assert!(is_known_binary(&macho_bytes));
+        assert!(is_known_binary(&coff_bytes));
+        assert!(is_known_binary(&wasm_bytes));
+        assert!(is_known_binary(&llvm_bytes));
+        assert!(!is_known_binary(&unknown_bytes));
+    }
+}

```

</details>
