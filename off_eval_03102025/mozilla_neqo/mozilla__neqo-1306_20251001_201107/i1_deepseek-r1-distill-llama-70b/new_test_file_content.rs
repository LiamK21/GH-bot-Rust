#neqo-http3/src/headers_checks.rs
// Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
// http://www.apache.org/licenses/LICENSE-2.0> or the MIT license
// <LICENSE-MIT or http://opensource.org/licenses/MIT>, at your
// option. This file may not be copied, modified, or distributed
// except according to those terms.

use crate::{Error, MessageType, Res};
use neqo_common::Header;

const PSEUDO_HEADER_STATUS: u8 = 0x1;
const PSEUDO_HEADER_METHOD: u8 = 0x2;
const PSEUDO_HEADER_SCHEME: u8 = 0x4;
const PSEUDO_HEADER_AUTHORITY: u8 = 0x8;
const PSEUDO_HEADER_PATH: u8 = 0x10;
const PSEUDO_HEADER_PROTOCOL: u8 = 0x20;
const REGULAR_HEADER: u8 = 0x80;

/// Check whether the response is informational(1xx).
/// # Errors
/// Returns an error if response headers do not contain
/// a status header or if the value of the header cannot be parsed.
pub fn is_interim(headers: &[Header]) -> Res<bool> {
    let status = headers.iter().take(1).find(|h| h.name() == ":status");
    if let Some(h) = status {
        #[allow(clippy::map_err_ignore)]
        let status_code = h.value().parse::<i32>().map_err(|_| Error::InvalidHeader)?;
        Ok((100..200).contains(&status_code))
    } else {
        Err(Error::InvalidHeader)
    }
}

fn track_pseudo(name: &str, state: &mut u8, message_type: MessageType) -> Res<bool> {
    let (pseudo, bit) = if name.starts_with(':') {
        if *state & REGULAR_HEADER != 0 {
            return Err(Error::InvalidHeader);
        }
        let bit = match (message_type, name) {
            (MessageType::Response, ":status") => PSEUDO_HEADER_STATUS,
            (MessageType::Request, ":method") => PSEUDO_HEADER_METHOD,
            (MessageType::Request, ":scheme") => PSEUDO_HEADER_SCHEME,
            (MessageType::Request, ":authority") => PSEUDO_HEADER_AUTHORITY,
            (MessageType::Request, ":path") => PSEUDO_HEADER_PATH,
            (MessageType::Request, ":protocol") => PSEUDO_HEADER_PROTOCOL,
            (_, _) => return Err(Error::InvalidHeader),
        };
        (true, bit)
    } else {
        (false, REGULAR_HEADER)
    };

    if *state & bit == 0 || !pseudo {
        *state |= bit;
        Ok(pseudo)
    } else {
        Err(Error::InvalidHeader)
    }
}

/// Checks if request/response headers are well formed, i.e. contain
/// allowed pseudo headers and in a right order, etc.
/// # Errors
/// Returns an error if headers are not well formed.
pub fn headers_valid(headers: &[Header], message_type: MessageType) -> Res<()> {
    let mut method_value: Option<&str> = None;
    let mut pseudo_state = 0;
    for header in headers {
        let is_pseudo = track_pseudo(header.name(), &mut pseudo_state, message_type)?;

        let mut bytes = header.name().bytes();
        if is_pseudo {
            if header.name() == ":method" {
                method_value = Some(header.value());
            }
            let _ = bytes.next();
        }

        if bytes.any(|b| matches!(b, 0 | 0x10 | 0x13 | 0x3a | 0x41..=0x5a)) {
            return Err(Error::InvalidHeader); // illegal characters.
        }
    }
    // Clear the regular header bit, since we only check pseudo headers below.
    pseudo_state &= !REGULAR_HEADER;
    let pseudo_header_mask = match message_type {
        MessageType::Response => PSEUDO_HEADER_STATUS,
        MessageType::Request => {
            if method_value == Some(&"CONNECT".to_string()) {
                PSEUDO_HEADER_METHOD | PSEUDO_HEADER_AUTHORITY
            } else {
                PSEUDO_HEADER_METHOD | PSEUDO_HEADER_SCHEME | PSEUDO_HEADER_PATH
            }
        }
    };

    if (MessageType::Request == message_type)
        && ((pseudo_state & PSEUDO_HEADER_PROTOCOL) > 0)
        && method_value != Some(&"CONNECT".to_string())
    {
        return Err(Error::InvalidHeader);
    }

    if pseudo_state & pseudo_header_mask != pseudo_header_mask {
        return Err(Error::InvalidHeader);
    }

    Ok(())
}

/// Checks if trailers are well formed, i.e. pseudo headers are not
/// allowed in trailers.
/// # Errors
/// Returns an error if trailers are not well formed.
pub fn trailers_valid(headers: &[Header]) -> Res<()> {
    for header in headers {
        if header.name().starts_with(':') {
            return Err(Error::InvalidHeader);
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {


#[test]
fn test_pseudo_header_tracking() {
    // Test case 1: Valid request headers
    let headers = vec![
        Header(":method".into(), "GET".into()),
        Header(":scheme".into(), "http".into()),
        Header(":path".into(), "/".into()),
        Header("accept".into(), "*/*".into()),
    ];
    let result = headers_valid(&headers, MessageType::Request);
    assert!(result.is_ok());

    // Test case 2: Missing required pseudo headers for request
    let headers = vec![
        Header(":method".into(), "GET".into()),
        Header(":scheme".into(), "http".into()),
        Header("accept".into(), "*/*".into()),
    ];
    let result = headers_valid(&headers, MessageType::Request);
    assert!(result.is_err());

    // Test case 3: Invalid pseudo header for response
    let headers = vec![
        Header(":status".into(), "200".into()),
        Header("content-type".into(), "text/plain".into()),
    ];
    let result = headers_valid(&headers, MessageType::Response);
    assert!(result.is_ok());

    // Test case 4: Duplicate pseudo header
    let headers = vec![
        Header(":method".into(), "GET".into()),
        Header(":method".into(), "POST".into()),
        Header(":scheme".into(), "http".into()),
        Header(":path".into(), "/".into()),
    ];
    let result = headers_valid(&headers, MessageType::Request);
    assert!(result.is_err());

    // Test case 5: Regular header mixed with pseudo
    let headers = vec![
        Header(":method".into(), "GET".into()),
        Header(":scheme".into(), "http".into()),
        Header("user-agent".into(), "Test".into()),
        Header(":path".into(), "/".into()),
    ];
    let result = headers_valid(&headers, MessageType::Request);
    assert!(result.is_ok());

    // Test case 6: Invalid message type for pseudo header
    let headers = vec![Header(":status".into(), "200".into())];
    let result = headers_valid(&headers, MessageType::Request);
    assert!(result.is_err());
}
}
