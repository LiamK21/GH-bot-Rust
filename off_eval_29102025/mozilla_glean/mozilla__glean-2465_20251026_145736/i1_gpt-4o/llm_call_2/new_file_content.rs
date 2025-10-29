#glean-core/src/traits/timing_distribution.rs
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

use crate::metrics::DistributionData;
use crate::metrics::TimerId;
use crate::ErrorType;

/// A description for the [`TimingDistributionMetric`](crate::metrics::TimingDistributionMetric) type.
///
/// When changing this trait, make sure all the operations are
/// implemented in the related type in `../metrics/`.
pub trait TimingDistribution {
    /// Start tracking time for the provided metric.
    /// Multiple timers can run simultaneously.
    ///
    /// # Returns
    ///
    /// A unique [`TimerId`] for the new timer.
    fn start(&self) -> TimerId;

    /// Stops tracking time for the provided metric and associated timer id.
    ///
    /// Adds a count to the corresponding bucket in the timing distribution.
    /// This will record an error if no [`start`](TimingDistribution::start) was
    /// called.
    ///
    /// # Arguments
    ///
    /// * `id` - The [`TimerId`] to associate with this timing. This allows
    ///   for concurrent timing of events associated with different ids to the
    ///   same timespan metric.
    fn stop_and_accumulate(&self, id: TimerId);

    /// Aborts a previous [`start`](TimingDistribution::start) call. No
    /// error is recorded if no [`start`](TimingDistribution::start) was
    /// called.
    ///
    /// # Arguments
    ///
    /// * `id` - The [`TimerId`] to associate with this timing. This allows
    ///   for concurrent timing of events associated with different ids to the
    ///   same timing distribution metric.
    fn cancel(&self, id: TimerId);

    /// Accumulates the provided signed samples in the metric.
    ///
    /// This is required so that the platform-specific code can provide us with
    /// 64 bit signed integers if no `u64` comparable type is available. This
    /// will take care of filtering and reporting errors for any provided negative
    /// sample.
    ///
    /// Please note that this assumes that the provided samples are already in
    /// the "unit" declared by the instance of the metric type (e.g. if the
    /// instance this method was called on is using [`crate::TimeUnit::Second`], then
    /// `samples` are assumed to be in that unit).
    ///
    /// # Arguments
    ///
    /// * `samples` - The vector holding the samples to be recorded by the metric.
    ///
    /// ## Notes
    ///
    /// Discards any negative value in `samples` and report an [`ErrorType::InvalidValue`]
    /// for each of them. Reports an [`ErrorType::InvalidOverflow`] error for samples that
    /// are longer than `MAX_SAMPLE_TIME`.
    fn accumulate_samples(&self, samples: Vec<i64>);

    /// Accumulates the provided samples in the metric.
    ///
    /// # Arguments
    ///
    /// * `samples` - A list of samples recorded by the metric.
    ///               Samples must be in nanoseconds.
    /// ## Notes
    ///
    /// Reports an [`ErrorType::InvalidOverflow`] error for samples that
    /// are longer than `MAX_SAMPLE_TIME`.
    fn accumulate_raw_samples_nanos(&self, samples: Vec<u64>);

    /// **Exported for test purposes.**
    ///
    /// Gets the currently stored value of the metric.
    ///
    /// This doesn't clear the stored value.
    ///
    /// # Arguments
    ///
    /// * `ping_name` - represents the optional name of the ping to retrieve the
    ///   metric for. Defaults to the first value in `send_in_pings`.
    fn test_get_value<'a, S: Into<Option<&'a str>>>(
        &self,
        ping_name: S,
    ) -> Option<DistributionData>;

    /// **Exported for test purposes.**
    ///
    /// Gets the number of recorded errors for the given error type.
    ///
    /// # Arguments
    ///
    /// * `error` - The type of error
    ///
    /// # Returns
    ///
    /// The number of errors recorded.
    fn test_get_num_recorded_errors(&self, error: ErrorType) -> i32;
}

#[cfg(test)]
mod tests {
use super::TimingDistribution;
use std::sync::Arc;
use std::sync::Mutex;
use crate::TimerId;
use crate::ErrorType;
use crate::DistributionData;

#[test]
fn test_accumulate_samples() {
    struct MockTimingDistribution {
        samples: Arc<Mutex<Vec<i64>>>,
    }

    impl TimingDistribution for MockTimingDistribution {
        fn start(&self) -> TimerId {
            TimerId(0)
        }

        fn stop_and_accumulate(&self, _id: TimerId) {}

        fn cancel(&self, _id: TimerId) {}

        fn accumulate_samples(&self, samples: Vec<i64>) {
            let mut stored_samples = self.samples.lock().unwrap();
            for sample in samples {
                if sample >= 0 {
                    stored_samples.push(sample);
                }
            }
        }

        fn accumulate_raw_samples_nanos(&self, _samples: Vec<u64>) {}

        fn test_get_value<'a, S: Into<Option<&'a str>>>(
            &self,
            _ping_name: S,
        ) -> Option<DistributionData> {
            None
        }

        fn test_get_num_recorded_errors(&self, _error: ErrorType) -> i32 {
            0
        }
    }

    let samples = Arc::new(Mutex::new(Vec::new()));
    let mock = MockTimingDistribution {
        samples: Arc::clone(&samples),
    };

    let input_samples = vec![100, -50, 200, -10, 300];
    mock.accumulate_samples(input_samples);

    let expected_samples = vec![100, 200, 300];
    let actual_samples = samples.lock().unwrap().clone();
    assert_eq!(expected_samples, actual_samples);
}
}
