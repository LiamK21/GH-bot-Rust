#glean-core/src/upload/util.rs
#[cfg(test)]
mod tests {
use std::fs::File;
use std::io::prelude::*;
use uuid::Uuid;
use super::process_pings_dir;
use crate::metrics::PingType;
use crate::tests::new_glean;

#[test]
fn test_ping_request_is_created_from_valid_ping_file() {
    let (mut glean, dir) = new_glean(None);
    let data_path = dir.path();

    let ping_type = PingType::new("test", true, true);
    glean.register_ping_type(&ping_type);

    glean.submit_ping(&ping_type).unwrap();

    let requests = process_pings_dir(&data_path).unwrap();

    assert_eq!(requests.len(), 1);

    let request_ping_type = requests[0]
        .body
        .get("ping_info")
        .and_then(|value| value.get("ping_type"))
        .unwrap();
    assert_eq!(request_ping_type, "test");
}
}
