#neqo-common/src/udp.rs
#[cfg(test)]
mod tests {
use neqo_common::udp;
use tokio::time::Sleep;
use std::net::SocketAddr;
use std::io;

#[test]
fn test_datagram_send_recv() {
  let sender = udp::Socket::bind("127.0.0.1:0").unwrap();
  let receiver_addr: SocketAddr = "127.0.0.1:0".parse().unwrap();
  let receiver = udp::Socket::bind(receiver_addr).unwrap();

  let datagram = neqo_common::Datagram::new(
    sender.local_addr().unwrap(),
    receiver.local_addr().unwrap(),
    neqo_common::IpTos::default(),
    None,
    "Hello, world!".as_bytes().to_vec(),
  );

  sender.writable().await.unwrap();
  sender.send(datagram.clone()).unwrap();

  receiver.readable().await.unwrap();
  let received_datagram = receiver.recv(&receiver.local_addr().unwrap()).unwrap().unwrap();

  assert_eq!(received_datagram.destination(), datagram.destination());
  assert_eq!(received_datagram.source(), datagram.source());
  assert_eq!(received_datagram.tos(), datagram.tos());
  assert_eq!(received_datagram.data(), datagram.data());
}
}
