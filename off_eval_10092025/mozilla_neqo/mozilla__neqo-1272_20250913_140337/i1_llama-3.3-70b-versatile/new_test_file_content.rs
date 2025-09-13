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
use log::Level;
use log::SetLoggerError;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

#[test]
fn test_dump_packet_logging() {
  let logger_called = Arc::new(AtomicBool::new(false));
  let logger_called_clone = logger_called.clone();
  let _ = log::set_logger(&object::Object::new(move |record| {
    if record.level() == Level::Debug {
      logger_called_clone.store(true, Ordering::SeqCst);
    }
  }));
  let _ = log::set_max_level(Level::Info);
  dump_packet("conn", "path", "dir", "pt", 1, &[1, 2, 3]);
  assert_eq!(false, logger_called.load(Ordering::SeqCst));
}
}
