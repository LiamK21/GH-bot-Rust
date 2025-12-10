#glean-core/src/upload/request.rs
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

//! Ping request representation.

use std::collections::HashMap;

use chrono::prelude::{DateTime, Utc};
use flate2::write::GzEncoder;
use flate2::Compression;
use serde_json::{self, Value as JsonValue};
use std::io::prelude::*;

/// Represents a request to upload a ping.
#[derive(PartialEq, Debug, Clone)]
pub struct PingRequest {
    /// The Job ID to identify this request,
    /// this is the same as the ping UUID.
    pub document_id: String,
    /// The path for the server to upload the ping to.
    pub path: String,
    /// The body of the request, as a byte array. If gzip encoded, then
    /// the `headers` list will contain a `Content-Encoding` header with
    /// the value `gzip`.
    pub body: Vec<u8>,
    /// A map with all the headers to be sent with the request.
    pub headers: HashMap<&'static str, String>,
}

impl PingRequest {
    /// Creates a new PingRequest.
    ///
    /// Automatically creates the default request headers.
    /// Clients may add more headers such as `userAgent` to this list.
    pub fn new(document_id: &str, path: &str, body: JsonValue) -> Self {
        // We want uploads to be gzip'd. Instead of doing this for each platform
        // we have language bindings for, apply compression here.
        let original_as_string = body.to_string();
        let gzipped_content = Self::gzip_content(path, original_as_string.as_bytes());
        let add_gzip_header = gzipped_content.is_some();
        let body = gzipped_content.unwrap_or_else(|| original_as_string.into_bytes());
        let body_len = body.len();

        Self {
            document_id: document_id.into(),
            path: path.into(),
            body,
            headers: Self::create_request_headers(add_gzip_header, body_len),
        }
    }

    /// Verifies if current request is for a deletion-request ping.
    pub fn is_deletion_request(&self) -> bool {
        // The path format should be `/submit/<app_id>/<ping_name>/<schema_version/<doc_id>`
        self.path
            .split('/')
            .nth(3)
            .map(|url| url == "deletion-request")
            .unwrap_or(false)
    }

    /// Attempt to gzip the provided ping content.
    fn gzip_content(path: &str, content: &[u8]) -> Option<Vec<u8>> {
        let mut gzipper = GzEncoder::new(Vec::new(), Compression::default());

        // Attempt to add the content to the gzipper.
        if let Err(e) = gzipper.write_all(content) {
            log::error!("Failed to write to the gzipper: {} - {:?}", path, e);
            return None;
        }

        gzipper.finish().ok()
    }

    /// Creates the default request headers.
    fn create_request_headers(is_gzipped: bool, body_len: usize) -> HashMap<&'static str, String> {
        let mut headers = HashMap::new();
        let date: DateTime<Utc> = Utc::now();
        headers.insert("Date", date.to_string());
        headers.insert("X-Client-Type", "Glean".to_string());
        headers.insert(
            "Content-Type",
            "application/json; charset=utf-8".to_string(),
        );
        headers.insert("Content-Length", body_len.to_string());
        if is_gzipped {
            headers.insert("Content-Encoding", "gzip".to_string());
        }
        headers.insert("X-Client-Version", crate::GLEAN_VERSION.to_string());
        headers
    }
}

#[cfg(test)]
mod tests {
use glean_core::src::upload::request::PingRequest;
use std::io::Cursor;
use flate2::read::GzDecoder;
use serde_json::json;
use serde_json::Value as JsonValue;

#[test]
fn test_pretty_body_decompresses_and_formats_payload() {
  // Create a test ping request with a gzip compressed payload
  let json_payload = json!({"key": "value"});
  let json_string = json_payload.to_string();
  let mut gzipper = flate2::write::GzEncoder::new(Vec::new(), flate2::Compression::default());
  gzipper.write_all(json_string.as_bytes()).unwrap();
  let compressed_payload = gzipper.finish().unwrap();

  let ping_request = PingRequest {
    document_id: "document_id".to_string(),
    path: "path".to_string(),
    body: compressed_payload,
  };

  // Test that pretty_body decompresses and formats the payload correctly
  let pretty_body = ping_request.pretty_body().unwrap();
  let expected_body = json_payload.to_string_pretty().unwrap();
  assert_eq!(pretty_body, expected_body);
}
}
