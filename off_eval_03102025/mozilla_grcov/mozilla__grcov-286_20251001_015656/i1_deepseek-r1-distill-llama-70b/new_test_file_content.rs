#src/covdir.rs
#[cfg(test)]
mod tests {
use super::CDStats;

#[test]
fn test_cdstats_calculation() {
    // Test case 1: Basic calculation
    let stats = CDStats::new(100, 75);
    assert_eq!(stats.total, 100);
    assert_eq!(stats.covered, 75);
    assert_eq!(stats.missed, 25);
    assert_eq!(stats.percent, 75.0);

    // Test case 2: Adding stats
    let mut stats1 = CDStats::new(50, 25);
    let stats2 = CDStats::new(50, 30);
    stats1.add(&stats2);
    stats1.set_percent();
    assert_eq!(stats1.total, 100);
    assert_eq!(stats1.covered, 55);
    assert_eq!(stats1.missed, 45);
    assert_eq!(stats1.percent, 55.0);

    // Test case 3: Zero total
    let stats = CDStats::new(0, 0);
    assert_eq!(stats.percent, 0.0);
}
}
