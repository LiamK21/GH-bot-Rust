#neqo-transport/src/connection/dump.rs
#[cfg(test)]
mod tests {
use std::fmt::Write;
use neqo_common::{qdebug, Decoder};
use super::dump_packet;
use log::Level;

#[test]
fn test_dump_packet_optimization() {
  let mut logger = log::Logger::root(log::MAX_LEVEL);
  logger.set_max_level(Level::Info);
  log::set_logger(&logger).unwrap();
  let conn = ();
  let path = ();
  let dir = "test";
  let pt = ();
  let pn = ();
  let payload = [1];
  dump_packet(&conn, &path, dir, pt, pn, &payload);
  logger.set_max_level(Level::Debug);
  log::set_logger(&logger).unwrap();
  dump_packet(&conn, &path, dir, pt, pn, &payload);
}
}
