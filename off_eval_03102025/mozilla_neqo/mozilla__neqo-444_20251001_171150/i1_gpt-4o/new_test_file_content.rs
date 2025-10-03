#neqo-http3/src/response_stream.rs
#[cfg(test)]
mod tests {
use super::ResponseStream;
use crate::client_events::Http3ClientEvents;
use crate::Header;
use neqo_transport::Connection;
use neqo_qpack::decoder::QPackDecoder;
use crate::hframe::HFrame;
use crate::Error;

#[test]
fn test_response_stream_read_headers() {
    let stream_id = 0;
    let conn_events = Http3ClientEvents::default();
    let mut response_stream = ResponseStream::new(stream_id, conn_events);
    let header_block = vec![0x01, 0x02, 0x03];
    let fin = false;

    response_stream.handle_headers_frame(header_block.clone(), fin).unwrap();

    let mut decoder = QPackDecoder::new(0, 0);
    response_stream.receive(&mut Connection::new_client("example.com", &["alpn"], &[]).unwrap(), &mut decoder).unwrap();

    let (headers, fin) = response_stream.read_response_headers().unwrap();
    assert_eq!(headers, vec![(String::from(":status"), String::from("200")), (String::from("content-length"), String::from("0"))]);
    assert_eq!(fin, false);
}
}
