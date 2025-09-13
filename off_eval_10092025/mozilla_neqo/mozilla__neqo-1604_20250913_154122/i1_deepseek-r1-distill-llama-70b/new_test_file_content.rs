#neqo-common/src/udp.rs
#[cfg(test)]
mod tests {
use super::udp::Socket;
use std::io;
use std::net::SocketAddr;
use tokio::test;

#[test]
fn test_datagram_tos() -> Result<(), io::Error> {
    let sender = Socket::bind("127.0.0.1:0")?;
    let receiver_addr: SocketAddr = "127.0.0.1:0".parse().unwrap();
    let receiver = Socket::bind(receiver_addr)?;

    let datagram = Datagram::new(
        sender.local_addr()?,
        receiver.local_addr()?,
        IpTos::from((IpTosDscp::Le, IpTosEcn::Ect1)),
        None,
        "Hello, world!".as_bytes().to_vec(),
    );

    sender.writable().await?;
    sender.send(datagram.clone())?;

    receiver.readable().await?;
    let received_datagram = receiver
        .recv(&receiver_addr)
        .expect("receive to succeed")
        .expect("receive to yield datagram");

    // Assert that the ECN is correct.
    assert_eq!(
        IpTosEcn::from(datagram.tos()),
        IpTosEcn::from(received_datagram.tos())
    );

    Ok(())
}
}
