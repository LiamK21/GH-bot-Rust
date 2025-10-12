#neqo-transport/src/connection/dump.rs
#[cfg(test)]
mod tests {
use neqo_common::{qdebug, Decoder};
use super::dump_packet;
use std::fmt::Write;
use log::Level;

#[test]
fn test_dump_packet_only_formats_when_debug_enabled() {
  let conn = ();
  let path = ();
  let dir = "dir";
  let pt = ();
  let pn = ();
  let payload = [0u8; 0];
  log::set_max_level(log::LevelFilter::Info);
  dump_packet(&conn, &path, &dir, pt, pn, &payload);
  log::set_max_level(log::LevelFilter::Debug);
  dump_packet(&conn, &path, &dir, pt, pn, &payload);
}
}
