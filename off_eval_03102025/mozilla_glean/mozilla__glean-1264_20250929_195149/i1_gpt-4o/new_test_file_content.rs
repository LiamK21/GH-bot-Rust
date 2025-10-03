#glean-core/src/traits/boolean.rs
#[cfg(test)]
mod tests {
use super::Boolean;
use crate::metrics::BooleanMetric;
use crate::metrics::CommonMetricData;

#[test]
fn test_boolean_set_and_get() {
    let metric = BooleanMetric::new(CommonMetricData::new("test", "test", "test"));
    metric.set(true);
    let expected = Some(true);
    let actual = metric.test_get_value("test");
    assert_eq!(expected, actual);
}
}
