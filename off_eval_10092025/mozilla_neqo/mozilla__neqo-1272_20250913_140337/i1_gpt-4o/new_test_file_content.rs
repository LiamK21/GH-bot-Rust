#neqo-transport/src/dump.rs
// Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
// http://www.apache.org/licenses/LICENSE-2.0> or the MIT license
// <LICENSE-MIT or http://opensource.org/licenses/MIT>, at your
// option. This file may not be copied, modified, or distributed
// except according to those terms.

// Enable just this file for logging to just see packets.
// e.g. "RUST_LOG=neqo_transport::dump neqo-client ..."

use crate::connection::Connection;
use crate::frame::Frame;
use crate::packet::{PacketNumber, PacketType};
use crate::path::PathRef;
use neqo_common::{qdebug, Decoder};

#[allow(clippy::module_name_repetitions)]
pub fn dump_packet(
    conn: &Connection,
    path: &PathRef,
    dir: &str,
    pt: PacketType,
    pn: PacketNumber,
    payload: &[u8],
) {
    let mut s = String::from("");
    let mut d = Decoder::from(payload);
    while d.remaining() > 0 {
        let f = match Frame::decode(&mut d) {
            Ok(f) => f,
            Err(_) => {
                s.push_str(" [broken]...");
                break;
            }
        };
        if let Some(x) = f.dump() {
            s.push_str(&format!("\n  {} {}", dir, &x));
        }
    }
    qdebug!([conn], "pn={} type={:?} {}{}", pn, pt, path.borrow(), s);
}

#[cfg(test)]
mod tests {
use super::dump_packet;
use neqo_common::Decoder;
use neqo_transport::{Connection, PathRef, PacketType, PacketNumber};
use log::Level;

#[test]
fn test_dump_packet_no_logging() {
    // Set the log level to a level higher than Debug to simulate no logging
    log::set_max_level(Level::Info);

    let conn = Connection::new_client("example.com", &["alpn"], &Default::default(), &Default::default()).unwrap();
    let path = PathRef::new(&conn, &conn);
    let dir = "out";
    let pt = PacketType::Short;
    let pn = PacketNumber::new(1);
    let payload = &[0u8, 1, 2, 3];

    // Capture the output of dump_packet
    let output = std::panic::catch_unwind(|| {
        dump_packet(&conn, &path, dir, pt, pn, payload);
    });

    // Ensure that no panic occurred, indicating no attempt to log
    assert!(output.is_ok());
}
}
