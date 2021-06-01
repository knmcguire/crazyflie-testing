import pytest
import time
import struct

import numpy as np

import cflib.crtp
from cflib.crtp.crtpstack import CRTPPacket
from cflib.crtp.crtpstack import CRTPPort

import conftest

RADIO_LATENCY_THRESSHOLD = 8  # ms
RADIO_BANDWIDTH_THRESSHOLD_BIG = 800  # packets/s
RADIO_BANDWIDTH_THRESSHOLD_SMALL = 400  # packets/s


@pytest.mark.parametrize('dev', conftest.get_devices(), ids=lambda d: d.name)
class TestRadio:
    def test_latency(self, dev):
        '''
        Test of requirements: RL001, RL003
        '''
        # Packet size 4
        assert(latency(dev.link_uri, 4) < RADIO_LATENCY_THRESSHOLD)

        # Packet size 28
        assert(latency(dev.link_uri, 28) < RADIO_LATENCY_THRESSHOLD)

    def test_bandwidth(self, dev):
        '''
        Test of requirements: RL003, RL004
        '''
        # Packet size 4
        assert(bandwidth(dev.link_uri, 4) > RADIO_BANDWIDTH_THRESSHOLD_BIG)

        # Packet size 28
        assert(bandwidth(dev.link_uri, 28) > RADIO_BANDWIDTH_THRESSHOLD_SMALL)


def build_data(i, packet_size):
    assert(packet_size % 4 == 0)
    repeats = packet_size // 4
    return struct.pack('<' + 'I'*repeats, *[i]*repeats)


def latency(uri, packet_size=4, count=500):
    link = cflib.crtp.get_link_driver(uri)

    pk = CRTPPacket()
    pk.set_header(CRTPPort.LINKCTRL, 0)  # Echo channel

    latencies = []
    for i in range(count):
        pk.data = build_data(i, packet_size)

        start_time = time.time()
        link.send_packet(pk)
        while True:
            pk_ack = link.receive_packet(-1)
            if pk_ack.port == CRTPPort.LINKCTRL and pk_ack.channel == 0:
                break
        end_time = time.time()

        # make sure we actually received the expected value
        i_recv, = struct.unpack('<I', pk_ack.data[0:4])
        assert(i == i_recv)
        latencies.append((end_time - start_time) * 1000)
    link.close()
    result = np.min(latencies)
    return result


def bandwidth(uri, packet_size=4, count=500):
    link = cflib.crtp.get_link_driver(uri)

    # enqueue packets
    start_time = time.time()
    for i in range(count):
        pk = CRTPPacket()
        pk.set_header(CRTPPort.LINKCTRL, 0)  # Echo channel
        pk.data = build_data(i, packet_size)
        link.send_packet(pk)

    # get the result
    for i in range(count):
        while True:
            pk_ack = link.receive_packet(-1)
            if pk_ack.port == CRTPPort.LINKCTRL and pk_ack.channel == 0:
                break
        # make sure we actually received the expected value
        i_recv, = struct.unpack('<I', pk_ack.data[0:4])
        assert(i_recv == i)
    end_time = time.time()
    link.close()
    result = count / (end_time - start_time)
    return result
