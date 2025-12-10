#glean-core/rlb/src/private/uuid.rs
#[cfg(test)]
mod tests {
use super::UuidMetric;
use uuid::Uuid;

#[test]
fn test_uuid_test_get_value_returns_uuid() {
    let metric = UuidMetric::new(glean_core::CommonMetricData {
        identifier: "test_uuid".into(),
        send_in_pings: vec!["test_ping".into()],
        ..Default::default()
    });
    let expected_uuid = Uuid::parse_str("936da01f-9ab9-4bcf-805e-85c1d0f8952c").unwrap();
    metric.set(expected_uuid);
    let actual = metric.test_get_value(None);
    assert!(actual.is_some());
    let actual_uuid = actual.unwrap();
    assert_eq!(expected_uuid, actual_uuid);
}
}
