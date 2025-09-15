#glean-core/src/thread.rs
#[cfg(test)]
mod tests {
use super::thread;
use std::thread;
use std::sync::atomic::{AtomicBool, Ordering};

#[test]
fn test_thread_registration() {
  let registered = AtomicBool::new(false);
  let handle = thread::spawn("test_thread", move || {
    registered.store(true, Ordering::SeqCst);
  });
  handle.join().unwrap();
  assert!(registered.load(Ordering::SeqCst));
}
}
