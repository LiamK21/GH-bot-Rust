#glean-core/rlb/src/private/memory_distribution.rs
#[cfg(test)]
mod tests {
use super::MemoryDistributionMetric;
use glean_core::metrics::MemoryUnit;
use glean_core::CommonMetricData;
use glean_core::traits::MemoryDistribution;

#[test]
fn test_memory_distribution_accumulate() {
    let meta = CommonMetricData {
        name: "test_memory_distribution".into(),
        category: "test".into(),
        send_in_pings: vec!["test_ping".into()],
        ..Default::default()
    };
    let memory_metric = MemoryDistributionMetric::new(meta, MemoryUnit::Byte);

    memory_metric.accumulate(1024);

    let expected = Some(DistributionData {
        sum: 1024,
        ..Default::default()
    });
    let actual = memory_metric.test_get_value("test_ping");

    assert_eq!(expected, actual);
}
}
