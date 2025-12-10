#glean-core/rlb/src/private/datetime.rs
#[cfg(test)]
mod tests {
use super::DatetimeMetric;
use crate::common_test::{lock_test, new_glean};
use crate::CommonMetricData;
use chrono::prelude::*;
use glean_core::metrics::TimeUnit;
use glean_core::ErrorType;

#[test]
fn test_datetime_set_and_get_value() {
    let _lock = lock_test();
    let _t = new_glean(None, true);

    let metric: DatetimeMetric = DatetimeMetric::new(
        CommonMetricData {
            name: "datetime".into(),
            category: "test".into(),
            send_in_pings: vec!["test1".into()],
            ..Default::default()
        },
        TimeUnit::Day,
    );

    let sample_date = FixedOffset::east(0).ymd(2023, 10, 5).and_hms(14, 30, 0);
    metric.set(Some(sample_date));

    let date = metric.test_get_value(None).unwrap();
    assert_eq!(date, FixedOffset::east(0).ymd(2023, 10, 5).and_hms(0, 0, 0));

    assert_eq!(
        metric.test_get_num_recorded_errors(ErrorType::InvalidValue, None),
        0
    );
}
}
