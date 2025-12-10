#glean-core/src/traits/boolean.rs
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

/// A description for the `BooleanMetric` type.
///
/// When changing this trait, make sure all the operations are
/// implemented in the related type in `../metrics/`.
pub trait Boolean {
    /// Sets to the specified boolean value.
    ///
    /// # Arguments
    ///
    /// * `value` - the value to set.
    fn set(&self, value: bool);

    /// **Exported for test purposes.**
    ///
    /// Gets the currently stored value as a boolean.
    ///
    /// This doesn't clear the stored value.
    fn test_get_value(&self, storage_name: &str) -> Option<bool>;
}

#[cfg(test)]
mod tests {
use super::BooleanMetric;
use glean_core::metrics::BooleanMetric as GleanBooleanMetric;

#[test]
fn test_test_get_value_without_ping_name() {
  let metric = BooleanMetric(GleanBooleanMetric::new("test_metric", "test_description", None));
  let result = metric.test_get_value(None);
  assert!(result.is_some());
}
}
