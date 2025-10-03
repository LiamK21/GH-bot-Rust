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
use glean_core::metrics::UuidMetric;
use glean_core::traits::Uuid;
use uuid::Uuid;

#[test]
fn test_uuid_set_get() {
  let metric_id = 1;
  let storage_name = "test_storage";
  let uuid_value = Uuid::new_v4();
  let glean_uuidmetric = UuidMetric::new(glean_core::CommonMetricData {
    lifetime: glean_core::Lifetime::Ping,
    ..Default::default()
  });
  glean_uuidmetric.set(uuid_value);
  let actual = glean_uuidmetric.test_get_value(storage_name).unwrap();
  assert_eq!(uuid_value, actual);
}
}
