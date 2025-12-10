#glean-core/rlb/src/dispatcher/global.rs
#[cfg(test)]
mod tests {
use super::launch;
use std::sync::{Arc, Mutex};
use std::thread;

#[test]
fn test_launch_off_main_thread() {
  let main_thread_id = thread::current().id();
  let thread_canary = Arc::new(Mutex::new(false));

  let canary_clone = Arc::clone(&thread_canary);
  launch(move || {
    let current_thread_id = thread::current().id();
    assert!(current_thread_id != main_thread_id);
    *canary_clone.lock().unwrap() = true;
  });

  thread::sleep(std::time::Duration::from_millis(50));
  assert!(*thread_canary.lock().unwrap());
}
}
