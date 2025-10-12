#glean-core/src/thread.rs
#[cfg(test)]
mod tests {
use std::thread;
use std::io;

#[test]
fn test_thread_registration() {
  let handle = thread::spawn("test_thread", || {});
  assert!(handle.join().is_ok());
}
}
