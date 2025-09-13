#neqo-common/src/udp.rs
#[cfg(test)]
mod tests {
use super::Datagram;
use super::IpTos;
use neqo_common::IpTosDscp;
use neqo_common::IpTosEcn;
use tokio::test;
use udp::Socket;

#[test]
fn test_datagram_ip_tos() {
  let sender = Socket::bind("127.0.0.1:0").unwrap();
  let receiver_addr: std::net::SocketAddr = "127.0.0.1:0".parse().unwrap();
  let receiver = Socket::bind(receiver_addr).unwrap();

  let datagram = Datagram::new(
      sender.local_addr().unwrap(),
      receiver.local_addr().unwrap(),
      IpTos::from((IpTosDscp::Le, IpTosEcn::Ect1)),
      None,
      "Hello, world!".as_bytes().to_vec(),
  );

  sender.writable().await.unwrap();
  sender.send(datagram.clone()).unwrap();

  receiver.readable().await.unwrap();
  let received_datagram = receiver.recv(&receiver_addr).unwrap().unwrap();

  assert_eq!(
      IpTosEcn::from(datagram.tos()),
      IpTosEcn::from(received_datagram.tos())
  );
}
}
