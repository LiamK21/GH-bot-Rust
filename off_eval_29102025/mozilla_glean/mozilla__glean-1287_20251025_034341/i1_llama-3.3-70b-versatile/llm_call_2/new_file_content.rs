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
    ///
    /// # Arguments
    ///
    /// * `ping_name` - represents the optional name of the ping to retrieve the
    ///   metric for. Defaults to the first value in `send_in_pings`.
    fn test_get_value<'a, S: Into<Option<&'a str>>>(&self, ping_name: S) -> Option<bool>;
}

#[cfg(test)]
mod tests {
use super::BooleanMetric;
use std::sync::Arc;

#[test]
fn test_boolean_metric_test_get_value() {
  let boolean_metric = BooleanMetric::new("test_metric", "test_category", "test_description", None, None);
  let expected_value = Some(true);
  boolean_metric.set(true);
  let actual_value = boolean_metric.test_get_value(None);
  assert_eq!(actual_value, expected_value);
}
}
