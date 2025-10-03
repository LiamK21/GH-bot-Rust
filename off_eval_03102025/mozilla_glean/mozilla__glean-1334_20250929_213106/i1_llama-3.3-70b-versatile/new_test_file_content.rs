#glean-core/rlb/src/private/quantity.rs
#[cfg(test)]
mod tests {
use glean_core::metrics::QuantityMetric;
use glean_core::traits::Quantity;
use glean_core::ErrorType;

#[test]
fn test_quantity_metric() {
  let metric = QuantityMetric::new(glean_core::CommonMetricData {
    name: "test_quantity".to_string(),
    category: "test_category".to_string(),
    send_in_pings: vec!["test_ping".to_string()],
    ..Default::default()
  });

  metric.set(10);
  assert_eq!(metric.test_get_value("test_ping"), Some(10));

  metric.set(-1);
  assert_eq!(metric.test_get_value("test_ping"), Some(0));

  assert_eq!(metric.test_get_num_recorded_errors(ErrorType::InvalidValue, "test_ping"), 1);
}
}
