#glean-core/rlb/src/private/event.rs
#[cfg(test)]
mod tests {
use super::EventMetric;
use super::NoExtraKeys;
use crate::common_test::{lock_test, new_glean};
use crate::CommonMetricData;

#[test]
fn test_event_recording_with_extra_keys() {
  let _lock = lock_test();
  let _t = new_glean(None, true);

  #[derive(Debug, Clone, Copy, Hash, Eq, PartialEq)]
  enum SomeExtra {
    Key1,
    Key2,
  }

  impl crate::traits::ExtraKeys for SomeExtra {
    const ALLOWED_KEYS: &'static [&'static str] = &["key1", "key2"];

    fn index(self) -> i32 {
      match self {
        SomeExtra::Key1 => 0,
        SomeExtra::Key2 => 1,
      }
    }
  }

  let metric: EventMetric<SomeExtra> = EventMetric::new(CommonMetricData {
    name: "event".into(),
    category: "test".into(),
    send_in_pings: vec!["test1".into()],
    ..Default::default()
  });

  let mut map1 = std::collections::HashMap::new();
  map1.insert(SomeExtra::Key1, "1".into());
  metric.record(Some(map1));

  let mut map2 = std::collections::HashMap::new();
  map2.insert(SomeExtra::Key1, "1".into());
  map2.insert(SomeExtra::Key2, "2".into());
  metric.record(Some(map2));

  metric.record(None);

  let data = metric.test_get_value(None).expect("no event recorded");
  assert_eq!(3, data.len());
  assert!(data[0].timestamp <= data[1].timestamp);
  assert!(data[1].timestamp <= data[2].timestamp);

  let mut map = std::collections::HashMap::new();
  map.insert("key1".into(), "1".into());
  assert_eq!(Some(map), data[0].extra);

  let mut map = std::collections::HashMap::new();
  map.insert("key1".into(), "1".into());
  map.insert("key2".into(), "2".into());
  assert_eq!(Some(map), data[1].extra);

  assert_eq!(None, data[2].extra);
}
}
