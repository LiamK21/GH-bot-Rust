#glean-core/ffi/src/uuid.rs
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

use std::os::raw::c_char;

use ffi_support::FfiStr;

use crate::{
    define_metric, ffi_string_ext::FallibleToString, handlemap_ext::HandleMapExtension,
    with_glean_value, Lifetime,
};

define_metric!(UuidMetric => UUID_METRICS {
    new           -> glean_new_uuid_metric(),
    destroy       -> glean_destroy_uuid_metric,
});

#[no_mangle]
pub extern "C" fn glean_uuid_set(metric_id: u64, value: FfiStr) {
    with_glean_value(|glean| {
        UUID_METRICS.call_with_log(metric_id, |metric| {
            let value = value.to_string_fallible()?;
            if let Ok(uuid) = uuid::Uuid::parse_str(&value) {
                metric.set(glean, uuid);
            } else {
                log::error!(
                    "Unexpected `uuid` value coming from platform code '{}'",
                    value
                );
            }
            Ok(())
        })
    })
}

#[no_mangle]
pub extern "C" fn glean_uuid_test_has_value(metric_id: u64, storage_name: FfiStr) -> u8 {
    with_glean_value(|glean| {
        UUID_METRICS.call_infallible(metric_id, |metric| {
            metric
                .test_get_value(glean, storage_name.as_str())
                .is_some()
        })
    })
}

#[no_mangle]
pub extern "C" fn glean_uuid_test_get_value(metric_id: u64, storage_name: FfiStr) -> *mut c_char {
    with_glean_value(|glean| {
        UUID_METRICS.call_infallible(metric_id, |metric| {
            metric.test_get_value(glean, storage_name.as_str()).unwrap()
        })
    })
}

#[cfg(test)]
mod tests {
use super::glean_uuid_test_has_value;
use std::ffi::CString;
use std::os::raw::c_char;
use std::ptr;

#[test]
fn test_glean_uuid_test_has_value() {
    let metric_id = 1; // Example metric ID
    let storage_name = CString::new("test_storage").unwrap();
    let storage_name_ptr = storage_name.as_ptr();

    // Expected value before the patch
    let expected_before_patch = 0; // Assuming no value is set

    // Call the function and get the actual result
    let actual_before_patch = unsafe { glean_uuid_test_has_value(metric_id, storage_name_ptr) };

    // Compare expected and actual values before the patch
    assert_eq!(expected_before_patch, actual_before_patch);

    // Simulate setting a UUID value (this would be done by the patched code)
    // For the purpose of this test, assume the patched code sets a value
    let expected_after_patch = 1; // Assuming a value is set

    // Call the function again and get the actual result after the patch
    let actual_after_patch = unsafe { glean_uuid_test_has_value(metric_id, storage_name_ptr) };

    // Compare expected and actual values after the patch
    assert_eq!(expected_after_patch, actual_after_patch);
}
}
