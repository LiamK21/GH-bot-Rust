#glean-core/src/coverage.rs
#[cfg(test)]
mod tests {
use super::record_coverage;
use std::env;
use std::fs::{File, OpenOptions};
use std::io::{Read, Write};
use std::sync::Mutex;
use once_cell::sync::Lazy;

#[test]
fn test_record_coverage() {
    let filename = "test_coverage_output.txt";
    env::set_var("GLEAN_TEST_COVERAGE", filename);

    // Initialize the Lazy static
    let _ = Lazy::force(&super::COVERAGE_FILE);

    // Record a metric
    record_coverage("test_metric_id");

    // Read the file to verify the content
    let mut file = File::open(filename).unwrap();
    let mut content = String::new();
    file.read_to_string(&mut content).unwrap();

    // Clean up
    std::fs::remove_file(filename).unwrap();

    assert!(content.contains("test_metric_id"));
}
}
