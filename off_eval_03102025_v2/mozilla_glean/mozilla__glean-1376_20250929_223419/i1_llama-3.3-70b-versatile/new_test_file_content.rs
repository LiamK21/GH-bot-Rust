#glean-core/rlb/src/private/memory_distribution.rs
#[cfg(test)]
mod tests {
use glean_core::metrics::{DistributionData, MemoryUnit, MetricType};
use glean_core::ErrorType;
use super::MemoryDistributionMetric;
use glean_core::CommonMetricData;

#[test]
fn test_memory_distribution_metric() {
  let meta = CommonMetricData {
    name: "memory_distribution_test".to_string(),
    description: "test".to_string(),
    lifetime: glean_core::Lifetime::Ping,
    send_in_pings: vec!["test_ping".to_string()],
    ..Default::default()
  };

  let metric = MemoryDistributionMetric::new(meta, MemoryUnit::Byte);
  metric.accumulate(100);
  metric.accumulate(200);
  let actual = metric.test_get_value(None).unwrap();
  let expected = DistributionData { values: vec![100, 200], bucket_ranges: vec![(0, 100), (100, 200)] };
  assert_eq!(actual.values.len(), 2);
}
}
