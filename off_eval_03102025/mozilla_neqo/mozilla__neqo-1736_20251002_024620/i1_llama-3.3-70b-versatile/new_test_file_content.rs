#neqo-bin/src/udp.rs
#[cfg(test)]
mod tests {
use neqo_bin::udp::Socket;
use neqo_common::Datagram;
use tokio::net::UdpSocket;
use std::net::SocketAddr;

#[test]
fn test_send_and_receive_datagram() {
  let addr: SocketAddr = "127.0.0.1:0".parse().unwrap();
  let socket = Socket::bind(addr).unwrap();
  let destination = socket.local_addr().unwrap();
  let datagram = Datagram::new(destination, destination, 0, None, "Hello, world!".as_bytes().to_vec());
  socket.send(datagram.clone()).unwrap();
  let mut received_datagrams = socket.recv(&destination).unwrap();
  let received_datagram = received_datagrams.pop().unwrap();
  assert_eq!(datagram, received_datagram);
}
}
