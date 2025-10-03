#glean-core/src/upload/request.rs
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

//! Ping request representation.

use std::collections::HashMap;

use chrono::prelude::{DateTime, Utc};
use serde_json::Value as JsonValue;

/// Represents a request to upload a ping.
#[derive(PartialEq, Debug, Clone)]
pub struct PingRequest {
    /// The Job ID to identify this request,
    /// this is the same as the ping UUID.
    pub uuid: String,
    /// The path for the server to upload the ping to.
    pub path: String,
    /// The body of the request.
    pub body: JsonValue,
    /// A map with all the headers to be sent with the request.
    pub headers: HashMap<String, String>,
}

impl PingRequest {
    /// Creates a new PingRequest.
    ///
    /// Automatically creates the default request headers.
    /// Clients may add more headers such as `userAgent` to this list.
    pub fn new(uuid: &str, path: &str, body: JsonValue) -> Self {
        Self {
            uuid: uuid.into(),
            path: path.into(),
            body,
            headers: Self::create_request_headers(),
        }
    }

    pub fn is_deletion_request(&self) -> bool {
        // The path format should be `/submit/<app_id>/<ping_name>/<schema_version/<doc_id>`
        self.path
            .split('/')
            .nth(3)
            .map(|url| url == "deletion-request")
            .unwrap_or(false)
    }

    /// Creates the default request headers.
    fn create_request_headers() -> HashMap<String, String> {
        let mut headers = HashMap::new();
        let date: DateTime<Utc> = Utc::now();
        headers.insert("Date".to_string(), date.to_string());
        headers.insert("X-Client-Type".to_string(), "Glean".to_string());
        headers.insert(
            "Content-Type".to_string(),
            "application/json; charset=utf-8".to_string(),
        );
        headers.insert(
            "X-Client-Version".to_string(),
            env!("CARGO_PKG_VERSION").to_string(),
        );
        headers
    }
}

#[cfg(test)]
mod tests {
use super::PingRequest;
use serde_json::json;

#[test]
fn test_ping_request_new() {
    let document_id = "test-document-id";
    let path = "/test/path";
    let body = json!({"key": "value"});

    let request = PingRequest::new(document_id, path, body.clone());

    assert_eq!(request.document_id, document_id);
    assert_eq!(request.path, path);
    assert_eq!(request.body, body);
}
}
