#glean-core/src/traits/boolean.rs
#[cfg(test)]
mod tests {
use super::Boolean;
use crate::metrics::boolean::BooleanMetric;
use crate::metrics::CommonMetricData;

#[test]
fn test_boolean_set_and_get() {
  let meta = CommonMetricData {
    name: "test_boolean".to_string(),
    ..Default::default()
  };
  let metric = BooleanMetric::new(meta);
  metric.set(true);
  let stored_value = metric.test_get_value("test_boolean", );
  assert_eq!(stored_value, Some(true));
}
}
