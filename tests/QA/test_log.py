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
import conftest
import time

from collections import defaultdict

from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.syncLogger import SyncLogger


@pytest.mark.parametrize('test_setup', conftest.get_devices(), indirect=['test_setup'], ids=lambda d: d.name)
class TestLogVariables:

    def test_log_async(self, test_setup):
        ''' Make sure we receive ~100 rows 1 second at 100Hz '''
        requirement = conftest.get_requirement('logging.basic')
        config = init_log_max_bytes()
        rows = 0

        def log_callback(ts, data, config):
            nonlocal rows
            rows += 1
            assert_variables_included(data, config.variables)

        with SyncCrazyflie(test_setup.device.link_uri) as scf:
            scf.cf.log.add_config(config)
            config.data_received_cb.add_callback(log_callback)

            config.start()
            time.sleep(1)
            config.stop()

            # With 100 ms frequency we expect 100 rows, allow 3% diff
            assert abs(requirement['max_rate'] - rows) < 3

    def test_log_too_many_variables(self, test_setup):
        '''
        Make sure we get an AttributeError when adding more variables
        than logging.variables.max.
        '''
        def init_log_many_variables(name):
            config = LogConfig(name=name, period_in_ms=10)
            config.add_variable('stabilizer.roll', 'float')       # 1
            config.add_variable('stabilizer.pitch', 'float')      # 2
            config.add_variable('stabilizer.yaw', 'float')        # 3
            config.add_variable('stabilizer.thrust', 'uint16_t')  # 4

            config.add_variable('sys.canfly', 'uint8_t')          # 5
            config.add_variable('sys.isFlying', 'uint8_t')        # 6
            config.add_variable('sys.isTumbled', 'uint8_t')       # 7

            config.add_variable('radio.rssi', 'uint8_t')          # 8
            config.add_variable('radio.isConnected', 'uint8_t')   # 9

            config.add_variable('pm.batteryLevel', 'uint8_t')     # 10

            config.add_variable('health.motorPass', 'uint8_t')    # 11
            config.add_variable('health.batteryPass', 'uint8_t')  # 12

            return config

        requirement = conftest.get_requirement('logging.variables')
        configs = []
        for i in range(int(requirement['max'] / 12) + 1):
            configs.append(init_log_many_variables('ManyVariables_%d' % i))

        # We need to be connected to a Crazyflie to add a log config
        assert test_setup.device.connect_sync()

        for config in configs:
            test_setup.device.cf.log.add_config(config)

        with pytest.raises(AttributeError):
            for config in configs:
                config.start()

    def test_log_too_many_blocks(self, test_setup):
        '''
        Make sure we get an AttributeError when adding more blocks
        than logging.blocks.max.
        '''
        requirement = conftest.get_requirement('logging.blocks')
        configs = []
        for i in range(requirement['max'] + 1):
            configs.append(init_log_max_bytes('MaxGroup_%d' % i))

        # We need to be connected to a Crazyflie to add a log config
        assert test_setup.device.connect_sync()

        for config in configs:
            test_setup.device.cf.log.add_config(config)

        with pytest.raises(AttributeError):
            for config in configs:
                config.start()

    def test_log_too_much_per_block(self, test_setup):
        '''
        Make sure we get an AttributeError when adding more bytes
        than logging.blocks.max_payload to a LogConfig.
        '''
        config = init_log_max_bytes()

        # Adding one byte brings us to 27 bytes, and 26 (LogConfig.MAX_LEN) is max.
        config.add_variable('radio.rssi', 'uint8_t')

        # We need to be connected to a Crazyflie to add a log config
        assert test_setup.device.connect_sync()

        with pytest.raises(AttributeError):
            test_setup.device.cf.log.add_config(config)

    def test_log_stress(self, test_setup):
        '''
        Make sure we can receive all packets requested when having an effective
        rate of logging.rate packets/s.
        '''
        requirement = conftest.get_requirement('logging.rate')
        if test_setup.kalman_active:
            pytest.skip('Only on non-kalman')

        configs = []
        for i in range(int(requirement['limit_low'] / 100)):
            configs.append(init_log_max_bytes('MaxGroup_%d' % i))

        packets = defaultdict(lambda: 0)

        def stress_cb(ts, data, config):
            packets[config.name] += 1

        duration = 10.0
        with SyncCrazyflie(test_setup.device.link_uri) as scf:
            scf.cf.console.receivedChar.add_callback(lambda msg: print(msg))
            for config in configs:
                scf.cf.log.add_config(config)
                config.data_received_cb.add_callback(stress_cb)
                config.start()

            time.sleep(duration)

            for config in configs:
                config.stop()
                assert packets[config.name] >= duration * 100.0  # 100 Hz

            rate = sum(packets.values()) / duration
            assert rate >= requirement['limit_low']  # packets / second

    def test_log_sync(self, test_setup):
        ''' Make sure logging synchronous works '''
        requirement = conftest.get_requirement('logging.basic')
        config = init_log_max_bytes()

        with SyncCrazyflie(test_setup.device.link_uri) as scf:
            with SyncLogger(scf, config) as logger:
                for rows, (ts, data, config) in enumerate(logger):
                    assert_variables_included(data, config.variables)
                    if rows >= requirement['max_rate']:
                        break


def init_log_max_bytes(name='MaxGroup'):
    ''' 7 variables * MAX_GROUPS (16) = 112 which is < MAX_VARIABLES (128) '''
    config = LogConfig(name=name, period_in_ms=10)
    config.add_variable('stabilizer.roll', 'float')       # 04 bytes
    config.add_variable('stabilizer.pitch', 'float')      # 08 bytes
    config.add_variable('stabilizer.yaw', 'float')        # 12 bytes
    config.add_variable('stabilizer.thrust', 'uint16_t')  # 14 bytes

    config.add_variable('gyro.xVariance', 'float')        # 18 bytes
    config.add_variable('gyro.yVariance', 'float')        # 22 bytes
    config.add_variable('gyro.zVariance', 'float')        # 26 bytes

    return config


def assert_variables_included(data, variables):
    assert len(data) == len(variables)
    for v in variables:
        assert v.name in data
