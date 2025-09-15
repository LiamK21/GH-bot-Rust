#glean-core/src/traits/boolean.rs
#[cfg(test)]
mod tests {
use super::Boolean;
use super::BooleanMetric;

#[test]
fn test_boolean_set() {
  let metric = BooleanMetric::new(Default::default());
  metric.set(true);
  let expected = true;
  let actual = metric.test_get_value("test_storage", "test_metric").unwrap();
  assert_eq!(expected, actual);
}
}
