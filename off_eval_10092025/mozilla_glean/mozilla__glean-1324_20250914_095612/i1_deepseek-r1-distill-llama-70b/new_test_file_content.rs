#glean-core/src/metrics/string.rs
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

use crate::metrics::Metric;
use crate::metrics::MetricType;
use crate::storage::StorageManager;
use crate::util::truncate_string_at_boundary_with_error;
use crate::CommonMetricData;
use crate::Glean;

const MAX_LENGTH_VALUE: usize = 100;

/// A string metric.
///
/// Record an Unicode string value with arbitrary content.
/// Strings are length-limited to `MAX_LENGTH_VALUE` bytes.
#[derive(Clone, Debug)]
pub struct StringMetric {
    meta: CommonMetricData,
}

impl MetricType for StringMetric {
    fn meta(&self) -> &CommonMetricData {
        &self.meta
    }

    fn meta_mut(&mut self) -> &mut CommonMetricData {
        &mut self.meta
    }
}

// IMPORTANT:
//
// When changing this implementation, make sure all the operations are
// also declared in the related trait in `../traits/`.
impl StringMetric {
    /// Creates a new string metric.
    pub fn new(meta: CommonMetricData) -> Self {
        Self { meta }
    }

    /// Sets to the specified value.
    ///
    /// # Arguments
    ///
    /// * `glean` - The Glean instance this metric belongs to.
    /// * `value` - The string to set the metric to.
    ///
    /// ## Notes
    ///
    /// Truncates the value if it is longer than `MAX_STRING_LENGTH` bytes and logs an error.
    pub fn set<S: Into<String>>(&self, glean: &Glean, value: S) {
        if !self.should_record(glean) {
            return;
        }

        let s = truncate_string_at_boundary_with_error(glean, &self.meta, value, MAX_LENGTH_VALUE);

        let value = Metric::String(s);
        glean.storage().record(glean, &self.meta, &value)
    }

    /// **Test-only API (exported for FFI purposes).**
    ///
    /// Gets the currently stored value as a string.
    ///
    /// This doesn't clear the stored value.
    pub fn test_get_value(&self, glean: &Glean, storage_name: &str) -> Option<String> {
        match StorageManager.snapshot_metric(
            glean.storage(),
            storage_name,
            &self.meta.identifier(glean),
        ) {
            Some(Metric::String(s)) => Some(s),
            _ => None,
        }
    }
}

#[cfg(test)]
mod tests {
use super::StringMetric;
use crate::test_get_num_recorded_errors;
use crate::tests::new_glean;
use crate::ErrorType;

#[test]
fn test_setting_valid_string_records_value_and_no_errors() {
    let (glean, _) = new_glean(None);

    let metric = StringMetric::new(crate::CommonMetricData {
        name: "string_metric".into(),
        category: "test".into(),
        send_in_pings: vec!["store1".into()],
        lifetime: crate::Lifetime::Application,
        disabled: false,
        dynamic_label: None,
    });

    let sample_string = "valid_string";
    metric.set(sample_string);

    let stored_value = metric.test_get_value("store1").unwrap();
    assert_eq!(stored_value, sample_string);

    assert_eq!(
        0,
        metric.test_get_num_recorded_errors(ErrorType::InvalidOverflow, "store1")
    );
}
}
