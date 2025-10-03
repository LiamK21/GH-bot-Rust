#glean-core/rlb/src/dispatcher/global.rs
#[cfg(test)]
mod tests {
use super::launch;
use std::sync::Arc;
use std::sync::{Mutex, MutexGuard};
use std::thread;
use std::time::Duration;

#[test]
fn test_launch_off_main_thread() {
  let main_thread_id = thread::current().id();
  let thread_canary = Arc::new(Mutex::new(false));

  let canary_clone = Arc::clone(&thread_canary);
  launch(move || {
      let canary_clone = Arc::clone(&canary_clone);
      let result = canary_clone.lock().unwrap();
      *result = true;
      assert!(thread::current().id() != main_thread_id);
  });

  thread::sleep(Duration::from_millis(100));
  let canary_clone = Arc::clone(&thread_canary);
  let result: MutexGuard<bool> = canary_clone.lock().unwrap();
  assert_eq!(*result, true);
}
}
