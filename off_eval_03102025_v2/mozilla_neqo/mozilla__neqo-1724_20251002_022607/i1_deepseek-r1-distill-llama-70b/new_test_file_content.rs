#neqo-bin/src/bin/server/main.rs
#[cfg(test)]
mod tests {


#[test]
fn test_server_response() {
    let server_addr: SocketAddr = "127.0.0.1:4433".parse().unwrap();

    // Start the server in a separate thread
    let handle = thread::spawn(move || {
        let mut args = Args::parse();
        args.hosts = vec!["127.0.0.1:4433".to_string()];
        let mut runner = ServersRunner::new(args).unwrap();
        runner.run().unwrap();
    });

    // Give the server time to start
    thread::sleep(Duration::from_secs(1));

    // Send an HTTP GET request
    let client = reqwest::blocking::Client::new();
    let res = client.get("http://localhost:4433/").send().unwrap();

    // Verify the response
    let expected_status = 200;
    assert_eq!(res.status(), expected_status);

    // Shutdown the server
    handle.join().unwrap();
}
}
