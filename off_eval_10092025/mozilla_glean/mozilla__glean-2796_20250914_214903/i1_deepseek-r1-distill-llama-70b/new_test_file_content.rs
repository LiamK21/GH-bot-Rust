#glean-core/src/metrics/object.rs
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

use std::sync::Arc;

use crate::common_metric_data::CommonMetricDataInternal;
use crate::error_recording::{record_error, test_get_num_recorded_errors, ErrorType};
use crate::metrics::JsonValue;
use crate::metrics::Metric;
use crate::metrics::MetricType;
use crate::storage::StorageManager;
use crate::CommonMetricData;
use crate::Glean;

/// An object metric.
///
/// Record structured data.
/// The value must adhere to a predefined structure and is serialized into JSON.
#[derive(Clone, Debug)]
pub struct ObjectMetric {
    meta: Arc<CommonMetricDataInternal>,
}

impl MetricType for ObjectMetric {
    fn meta(&self) -> &CommonMetricDataInternal {
        &self.meta
    }
}

// IMPORTANT:
//
// When changing this implementation, make sure all the operations are
// also declared in the related trait in `../traits/`.
impl ObjectMetric {
    /// Creates a new object metric.
    pub fn new(meta: CommonMetricData) -> Self {
        Self {
            meta: Arc::new(meta.into()),
        }
    }

    /// Sets to the specified structure.
    ///
    /// # Arguments
    ///
    /// * `glean` - the Glean instance this metric belongs to.
    /// * `value` - the value to set.
    #[doc(hidden)]
    pub fn set_sync(&self, glean: &Glean, value: JsonValue) {
        let value = Metric::Object(serde_json::to_string(&value).unwrap());
        glean.storage().record(glean, &self.meta, &value)
    }

    /// Sets to the specified structure.
    ///
    /// No additional verification is done.
    /// The shape needs to be externally verified.
    ///
    /// # Arguments
    ///
    /// * `value` - the value to set.
    pub fn set(&self, value: JsonValue) {
        let metric = self.clone();
        crate::launch_with_glean(move |glean| metric.set_sync(glean, value))
    }

    /// Record an `InvalidValue` error for this metric.
    ///
    /// Only to be used by the RLB.
    // TODO(bug 1691073): This can probably go once we have a more generic mechanism to record
    // errors
    pub fn record_schema_error(&self) {
        let metric = self.clone();
        crate::launch_with_glean(move |glean| {
            let msg = "Value did not match predefined schema";
            record_error(glean, &metric.meta, ErrorType::InvalidValue, msg, None);
        });
    }

    /// Get current value
    #[doc(hidden)]
    pub fn get_value<'a, S: Into<Option<&'a str>>>(
        &self,
        glean: &Glean,
        ping_name: S,
    ) -> Option<String> {
        let queried_ping_name = ping_name
            .into()
            .unwrap_or_else(|| &self.meta().inner.send_in_pings[0]);

        match StorageManager.snapshot_metric_for_test(
            glean.storage(),
            queried_ping_name,
            &self.meta.identifier(glean),
            self.meta.inner.lifetime,
        ) {
            Some(Metric::Object(o)) => Some(o),
            _ => None,
        }
    }

    /// **Test-only API (exported for FFI purposes).**
    ///
    /// Gets the currently stored value as JSON.
    ///
    /// This doesn't clear the stored value.
    pub fn test_get_value(&self, ping_name: Option<String>) -> Option<JsonValue> {
        crate::block_on_dispatcher();
        let value = crate::core::with_glean(|glean| self.get_value(glean, ping_name.as_deref()));
        // We only store valid JSON
        value.map(|val| serde_json::from_str(&val).unwrap())
    }

    /// **Exported for test purposes.**
    ///
    /// Gets the number of recorded errors for the given metric and error type.
    ///
    /// # Arguments
    ///
    /// * `error` - The type of error
    /// * `ping_name` - represents the optional name of the ping to retrieve the
    ///   metric for. inner to the first value in `send_in_pings`.
    ///
    /// # Returns
    ///
    /// The number of errors reported.
    pub fn test_get_num_recorded_errors(&self, error: ErrorType) -> i32 {
        crate::block_on_dispatcher();

        crate::core::with_glean(|glean| {
            test_get_num_recorded_errors(glean, self.meta(), error).unwrap_or(0)
        })
    }
}

#[cfg(test)]
mod tests {
use serde_json::json;
use super::ObjectMetric;
use glean::launch_with_glean;
use glean::ErrorType;
use glean::record_error;

#[test]
fn test_object_metric_set_string() {
    let metric = ObjectMetric::new("test_object");

    // Test valid JSON
    let expected_value = json!({"key": "value"});
    let mut actual_value = None;

    launch_with_glean(|glean| {
        metric.set_string(glean, serde_json::to_string(&expected_value).unwrap());
        let result = glean.storage().get::<String>(glean, &metric.meta);
        if let Some(value) = result {
            actual_value = Some(serde_json::from_str(&value).unwrap());
        }
    });

    assert_eq!(expected_value, actual_value.unwrap());

    // Test invalid JSON
    let invalid_json = "{invalid: json}";
    let mut error_recorded = false;

    launch_with_glean(|glean| {
        metric.set_string(glean, invalid_json.to_string());
        let errors = glean.storage().get_errors(glean, &metric.meta);
        if let Some(errors) = errors {
            for error in errors {
                if error.error_type == ErrorType::InvalidValue {
                    error_recorded = true;
                    break;
                }
            }
        }
    });

    assert!(error_recorded);
}
}
