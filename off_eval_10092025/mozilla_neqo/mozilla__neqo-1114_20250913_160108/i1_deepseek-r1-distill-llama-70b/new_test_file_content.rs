#neqo-transport/src/connection/params.rs
// Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
// http://www.apache.org/licenses/LICENSE-2.0> or the MIT license
// <LICENSE-MIT or http://opensource.org/licenses/MIT>, at your
// option. This file may not be copied, modified, or distributed
// except according to those terms.

use crate::recv_stream::RECV_BUFFER_SIZE;
use crate::stream_id::{StreamIndex, StreamType};
use crate::tparams::PreferredAddress;
use crate::{CongestionControlAlgorithm, QuicVersion};
use std::convert::TryFrom;

const LOCAL_MAX_DATA: u64 = 0x3FFF_FFFF_FFFF_FFFF; // 2^62-1
const LOCAL_STREAM_LIMIT_BIDI: StreamIndex = StreamIndex::new(16);
const LOCAL_STREAM_LIMIT_UNI: StreamIndex = StreamIndex::new(16);

/// What to do with preferred addresses.
#[derive(Debug, Clone)]
pub enum PreferredAddressConfig {
    /// Disabled, whether for client or server.
    Disabled,
    /// Enabled at a client, disabled at a server.
    Default,
    /// Enabled at both client and server.
    Address(PreferredAddress),
}

/// ConnectionParameters use for setting intitial value for QUIC parameters.
/// This collects configuration like initial limits, protocol version, and
/// congestion control algorithm.
#[derive(Debug, Clone)]
pub struct ConnectionParameters {
    quic_version: QuicVersion,
    cc_algorithm: CongestionControlAlgorithm,
    max_data: u64,
    max_stream_data_bidi: u64,
    max_stream_data_uni: u64,
    max_streams_bidi: StreamIndex,
    max_streams_uni: StreamIndex,
    preferred_address: PreferredAddressConfig,
}

impl Default for ConnectionParameters {
    fn default() -> Self {
        Self {
            quic_version: QuicVersion::default(),
            cc_algorithm: CongestionControlAlgorithm::NewReno,
            max_data: LOCAL_MAX_DATA,
            max_stream_data_bidi: u64::try_from(RECV_BUFFER_SIZE).unwrap(),
            max_stream_data_uni: u64::try_from(RECV_BUFFER_SIZE).unwrap(),
            max_streams_bidi: LOCAL_STREAM_LIMIT_BIDI,
            max_streams_uni: LOCAL_STREAM_LIMIT_UNI,
            preferred_address: PreferredAddressConfig::Default,
        }
    }
}

impl ConnectionParameters {
    pub fn get_quic_version(&self) -> QuicVersion {
        self.quic_version
    }

    pub fn quic_version(mut self, v: QuicVersion) -> Self {
        self.quic_version = v;
        self
    }

    pub fn get_cc_algorithm(&self) -> CongestionControlAlgorithm {
        self.cc_algorithm
    }

    pub fn cc_algorithm(mut self, v: CongestionControlAlgorithm) -> Self {
        self.cc_algorithm = v;
        self
    }

    pub fn get_max_data(&self) -> u64 {
        self.max_data
    }

    pub fn max_data(mut self, v: u64) -> Self {
        self.max_data = v;
        self
    }

    pub fn get_max_streams(&self, stream_type: StreamType) -> StreamIndex {
        match stream_type {
            StreamType::BiDi => self.max_streams_bidi,
            StreamType::UniDi => self.max_streams_uni,
        }
    }

    pub fn max_streams(mut self, stream_type: StreamType, v: StreamIndex) -> Self {
        assert!(v.as_u64() <= (1 << 60), "max_streams is too large");
        match stream_type {
            StreamType::BiDi => {
                self.max_streams_bidi = v;
            }
            StreamType::UniDi => {
                self.max_streams_uni = v;
            }
        }
        self
    }

    pub fn get_max_stream_data(&self, stream_type: StreamType) -> u64 {
        match stream_type {
            StreamType::BiDi => self.max_stream_data_bidi,
            StreamType::UniDi => self.max_stream_data_uni,
        }
    }

    pub fn max_stream_data(mut self, stream_type: StreamType, v: u64) -> Self {
        match stream_type {
            StreamType::BiDi => {
                self.max_stream_data_bidi = v;
            }
            StreamType::UniDi => {
                self.max_stream_data_uni = v;
            }
        }
        self
    }

    /// Set a preferred address (which only has an effect for a server).
    pub fn preferred_address(mut self, preferred: PreferredAddress) -> Self {
        self.preferred_address = PreferredAddressConfig::Address(preferred);
        self
    }

    /// Disable the use of preferred addresses.
    pub fn disable_preferred_address(mut self) -> Self {
        self.preferred_address = PreferredAddressConfig::Disabled;
        self
    }

    pub fn get_preferred_address(&self) -> &PreferredAddressConfig {
        &self.preferred_address
    }
}

#[cfg(test)]
mod tests {
use super::ConnectionParameters;
use super::Role;
use crate::connection::ConnectionIdManager;
use crate::tparams::TransportParametersHandler;
use std::result::Result as Res;

#[test]
fn test_transport_parameters_initialized_correctly() {
    let mut conn_params = ConnectionParameters::default();
    conn_params.set_max_data(1000);
    conn_params.set_max_stream_data(StreamType::BiDi, 2000);
    conn_params.set_max_stream_data(StreamType::UniDi, 3000);
    conn_params.set_max_streams(StreamType::BiDi, 4);
    conn_params.set_max_streams(StreamType::UniDi, 5);

    let mut cid_manager = ConnectionIdManager::new(&mut rand::thread_rng(), vec![1,2,3,4,5,6,7,8,9,10,11,12]);

    let role = Role::Client;
    let tps_result = conn_params.create_transport_parameter(role, &mut cid_manager);

    assert!(tps_result.is_ok());
    let tps = tps_result.unwrap();

    // Check default parameters
    let recv_buffer_size = tparams::INITIAL_MAX_STREAM_DATA_BIDI_REMOTE;
    let expected_recv_buffer_size = RECV_BUFFER_SIZE as u64;
    assert_eq!(tps.local.get_integer(recv_buffer_size).unwrap(), expected_recv_buffer_size);

    let idle_timeout = tparams::IDLE_TIMEOUT;
    let expected_idle_timeout = LOCAL_IDLE_TIMEOUT.as_millis() as u64;
    assert_eq!(tps.local.get_integer(idle_timeout).unwrap(), expected_idle_timeout);

    let active_cid_limit = tparams::ACTIVE_CONNECTION_ID_LIMIT;
    let expected_active_cid_limit = LOCAL_ACTIVE_CID_LIMIT as u64;
    assert_eq!(tps.local.get_integer(active_cid_limit).unwrap(), expected_active_cid_limit);

    // Check configurable parameters
    let initial_max_data = tparams::INITIAL_MAX_DATA;
    assert_eq!(tps.local.get_integer(initial_max_data).unwrap(), 1000);

    let initial_max_stream_data_bidi_local = tparams::INITIAL_MAX_STREAM_DATA_BIDI_LOCAL;
    assert_eq!(tps.local.get_integer(initial_max_stream_data_bidi_local).unwrap(), 2000);

    let initial_max_stream_data_uni_local = tparams::INITIAL_MAX_STREAM_DATA_UNI;
    assert_eq!(tps.local.get_integer(initial_max_stream_data_uni_local).unwrap(), 3000);

    let initial_max_streams_bidi = tparams::INITIAL_MAX_STREAMS_BIDI;
    assert_eq!(tps.local.get_integer(initial_max_streams_bidi).unwrap(), 4);

    let initial_max_streams_uni = tparams::INITIAL_MAX_STREAMS_UNI;
    assert_eq!(tps.local.get_integer(initial_max_streams_uni).unwrap(), 5);
}
}
