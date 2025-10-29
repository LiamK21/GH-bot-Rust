#glean-core/src/thread.rs
use std::io;
use std::thread::{self, JoinHandle};

#[cfg(all(feature = "gecko", not(target_os = "android")))]
mod bindings {
    extern "C" {
        pub fn gecko_profiler_register_thread(name: *const std::ffi::c_char);
        pub fn gecko_profiler_unregister_thread();
    }
}

/// Register a thread with the Gecko Profiler.
#[cfg(all(feature = "gecko", not(target_os = "android")))]
fn register_thread(thread_name: &str) {
    let name = std::ffi::CString::new(thread_name).unwrap();
    unsafe {
        // gecko_profiler_register_thread copies the passed name here.
        bindings::gecko_profiler_register_thread(name.as_ptr());
    }
}

#[cfg(any(not(feature = "gecko"), target_os = "android"))]
fn register_thread(_thread_name: &str) {}

/// Unregister a thread with the Gecko Profiler.
#[cfg(all(feature = "gecko", not(target_os = "android")))]
fn unregister_thread() {
    unsafe {
        bindings::gecko_profiler_unregister_thread();
    }
}
#[cfg(any(not(feature = "gecko"), target_os = "android"))]
fn unregister_thread() {}

/// Spawns a new thread, returning a [`JoinHandle`] for it.
///
/// Wrapper around [`std::thread::spawn`], but automatically naming the thread.
pub fn spawn<F, T>(name: &'static str, f: F) -> Result<JoinHandle<T>, io::Error>
where
    F: FnOnce() -> T + Send + 'static,
    T: Send + 'static,
{
    thread::Builder::new()
        .name(name.to_string())
        .spawn(move || {
            register_thread(name);
            let res = f();
            unregister_thread();
            res
        })
}

#[cfg(test)]
mod tests {
use std::thread;
use std::time::Duration;

#[cfg(all(feature = "gecko", not(target_os = "android")))]
mod gecko_thread_test {
    use super::*;

    static mut REGISTER_CALLED: bool = false;
    static mut UNREGISTER_CALLED: bool = false;

    #[no_mangle]
    pub unsafe extern "C" fn gecko_profiler_register_thread(_name: *const std::ffi::c_char) {
        REGISTER_CALLED = true;
    }

    #[no_mangle]
    pub unsafe extern "C" fn gecko_profiler_unregister_thread() {
        UNREGISTER_CALLED = true;
    }

    #[test]
    fn test_gecko_callbacks_called() {
        unsafe {
            REGISTER_CALLED = false;
            UNREGISTER_CALLED = false;
        }

        let handle = thread::spawn("test_gecko", move || {
            // Thread will call register and then unwind
            panic!("intentional panic to test unregistration")
        }).unwrap();

        handle.join().unwrap_err(); // Consume panic

        unsafe {
            assert!(REGISTER_CALLED, "Register was not called");
            assert!(UNREGISTER_CALLED, "Unregister was not called");
        }
    }
}
}
