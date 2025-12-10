#glean-core/rlb/src/private/event.rs
#[cfg(test)]
mod tests {
use super::EventMetric;
use super::NoExtraKeys;
use std::collections::HashMap;

#[test]
fn test_event_recording() {
  let metric: EventMetric<NoExtraKeys> = EventMetric::new(super::CommonMetricData {
    name: "event".into(),
    category: "test".into(),
    send_in_pings: vec!["test1".into()],
    ..Default::default()
  });
  metric.record(None);
  metric.record(None);
  let data = metric.test_get_value(None).expect("no event recorded");
  assert_eq!(2, data.len());
  assert!(data[0].timestamp <= data[1].timestamp);
}
}
