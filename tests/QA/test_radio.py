# Copyright (C) 2021 Bitcraze AB
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, in version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
import pytest
import time
import struct

import numpy as np

import cflib.crtp
from cflib.crtp.crtpstack import CRTPPacket
from cflib.crtp.crtpstack import CRTPPort

import conftest
import logging

time_start = 0

logger = logging.getLogger(__name__)


@pytest.mark.parametrize('dev', conftest.get_devices(), ids=lambda d: d.name)
class TestRadio:
    def test_latency_small_packets(self, dev):
        requirement = conftest.get_requirement('radio.latencysmall')
        assert(latency(dev.link_uri, requirement['packet_size']) < requirement['limit_high_ms'])

    def test_latency_big_packets(self, dev):
        requirement = conftest.get_requirement('radio.latencybig')
        assert(latency(dev.link_uri, requirement['packet_size']) < requirement['limit_high_ms'])

    def test_bandwidth_small_packets(self, dev):
        requirement = conftest.get_requirement('radio.bwsmall')
        assert(bandwidth(dev.link_uri, requirement['packet_size']) > requirement['limit_low'])

    def test_bandwidth_big_packets(self, dev):
        requirement = conftest.get_requirement('radio.bwbig')
        assert(bandwidth(dev.link_uri, requirement['packet_size']) > requirement['limit_low'])

    def test_reliability(self, dev):
        requirement = conftest.get_requirement('radio.reliability')
        # The bandwidth function will assert if there is any packet loss
        bandwidth(dev.link_uri, 4, requirement['limit_low'])


def build_data(i, packet_size):
    assert(packet_size % 4 == 0)
    repeats = packet_size // 4
    return struct.pack('<' + 'I' * repeats, *[i] * repeats)


def latency(uri, packet_size=4, count=500):
    link = cflib.crtp.get_link_driver(uri)

    try:
        pk = CRTPPacket()
        pk.set_header(CRTPPort.LINKCTRL, 0)  # Echo channel

        latencies = []
        for i in range(count):
            pk.data = build_data(i, packet_size)

            start_time = time.time()
            if not link.send_packet(pk):
                link.close()
                raise Exception("send_packet() timeout!")
            while True:
                pk_ack = link.receive_packet(2)
                if pk_ack is None:
                    link.close()
                    raise Exception("Receive packet timeout!")
                if pk_ack.port == CRTPPort.LINKCTRL and pk_ack.channel == 0:
                    break
            end_time = time.time()

            # make sure we actually received the expected value
            i_recv, = struct.unpack('<I', pk_ack.data[0:4])
            assert(i == i_recv)
            latencies.append((end_time - start_time) * 1000)
    except Exception as e:
        link.close()
        raise e

    link.close()
    min = np.min(latencies)
    mean = np.mean(latencies)
    max = np.max(latencies)

    logger.info(f'{uri}: Done @ {time.time() - time_start}')
    logger.info('latency: min {}, mean: {}, max: {}'.format(min, mean, max))

    return min


def bandwidth(uri, packet_size=4, count=500):
    link = cflib.crtp.get_link_driver(uri)

    try:
        # enqueue packets
        start_time = time.time()
        for i in range(count):
            pk = CRTPPacket()
            pk.set_header(CRTPPort.LINKCTRL, 0)  # Echo channel
            pk.data = build_data(i, packet_size)
            if not link.send_packet(pk):
                raise Exception("send_packet() timeout!")

        # get the result
        for i in range(count):
            while True:
                pk_ack = link.receive_packet(2)
                if pk_ack is None:
                    raise Exception("Receive packet timeout!")
                if pk_ack.port == CRTPPort.LINKCTRL and pk_ack.channel == 0:
                    break
            # make sure we actually received the expected value
            i_recv, = struct.unpack('<I', pk_ack.data[0:4])
            assert(i_recv == i)
        end_time = time.time()
    except Exception as e:
        link.close()
        raise e

    link.close()
    result = count / (end_time - start_time)
    logger.info('bandwidth: {}'.format(result))

    return result


def test_radio_fairness():
    global time_start

    swarm = conftest.get_swarm()
    record_bandwidth = dict()
    record_latency = dict()

    def bandwidth_fairness(scf):
        nonlocal record_bandwidth
        record_bandwidth[scf._link_uri] = bandwidth(scf._link_uri)

    def latency_fairness(scf):
        nonlocal record_latency
        record_latency[scf._link_uri] = latency(scf._link_uri)

    swarm.parallel_safe(bandwidth_fairness)

    time_start = time.time()

    swarm.parallel_safe(latency_fairness)
