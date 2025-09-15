#glean-core/rlb/src/private/uuid.rs
#[cfg(test)]
mod tests {
use super::UuidMetric;
use uuid::Uuid;
use glean_core::metrics::MetricType;
use glean_core::ErrorType;

#[test]
fn test_uuid_metric_set_and_get() {
  let metric = UuidMetric::new(glean_core::CommonMetricData::new("test_uuid_metric", MetricType::Uuid));
  let value = Uuid::new_v4();
  metric.set(value);
  let actual = metric.test_get_value(None);
  assert_eq!(actual.unwrap(), value);
}
}
