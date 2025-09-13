#neqo-bin/src/bin/client/main.rs
#[cfg(test)]
mod tests {
use super::Args;
use super::get_output_file;
use super::http3;
use super::http09;
use super::Runner;
use super::KeyUpdateState;
use neqo_common::udp::Socket;
use std::net::SocketAddr;
use url::Url;
use tokio::test;

#[test]
fn test_handle_client() {
    let mut args = Args::parse();
    let socket = Socket::bind("127.0.0.1:0").unwrap();
    let local_addr = socket.local_addr().unwrap();
    let remote_addr: SocketAddr = "127.0.0.1:8080".parse().unwrap();
    let hostname = "example.com";
    let mut urls = VecDeque::new();
    urls.push_back(Url::parse("https://example.com").unwrap());
    let key_update = KeyUpdateState(false);
    let resumption_token = None;
    let mut handler = http3::Handler::new(urls, &args, key_update);
    let mut client = http3::create_client(&args, local_addr, remote_addr, hostname, resumption_token).unwrap();
    let mut runner = Runner {
        local_addr,
        socket: &mut socket,
        client,
        handler,
        timeout: None,
        args: &args,
    };
    let result = test::block_on(runner.run());
    assert!(result.is_ok());
}
}
