#neqo-bin/src/bin/client.rs
#[cfg(test)]
mod tests {
use super::create_http3_client;
use neqo_common::udp::Socket;
use neqo_http3::Http3Client;
use neqo_transport::Connection;
use std::net::SocketAddr;
use std::str::FromStr;
use url::Url;

#[test]
fn test_create_http3_client() {
  let mut args = super::Args::default();
  let socket = Socket::bind("127.0.0.1:0").unwrap();
  let local_addr = socket.local_addr().unwrap();
  let remote_addr: SocketAddr = "127.0.0.1:443".parse().unwrap();
  let hostname = "example.com";
  let resumption_token = None;
  let _ = create_http3_client(&mut args, local_addr, remote_addr, hostname, resumption_token);
}
}
