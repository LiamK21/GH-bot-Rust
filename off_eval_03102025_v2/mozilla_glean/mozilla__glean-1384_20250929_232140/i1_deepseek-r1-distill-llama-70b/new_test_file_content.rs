#glean-core/rlb/src/private/datetime.rs
#[cfg(test)]
mod tests {
use super::DatetimeMetric;
use crate::common_test::{lock_test, new_glean};
use crate::CommonMetricData;
use chrono::prelude::*;

#[test]
fn test_datetime_error_handling() {
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

    // Attempting to set an invalid date (February 30th)
    let invalid_date = FixedOffset::east(0).ymd(2020, 2, 30).and_hms(0, 0, 0);
    metric.set(Some(invalid_date));

    // Verify that the stored value is None due to invalid date
    let stored_value = metric.test_get_value(None);
    assert!(stored_value.is_none());

    // Check that an InvalidValue error was recorded
    let error_count = metric.test_get_num_recorded_errors(ErrorType::InvalidValue, None);
    assert_eq!(error_count, 1);
}
}
