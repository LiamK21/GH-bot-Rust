#tools/embedded-uniffi-bindgen/src/lib.rs
#[cfg(test)]
mod tests {
use glean::BooleanMetric;

#[test]
fn test_clone_booleanmetric() {
    let metric = BooleanMetric::new();
    let _ = metric.clone();
    assert!(metric.is_initialized());
}
}
