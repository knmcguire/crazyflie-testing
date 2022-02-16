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
import logging
import time
import random

from cflib.crazyflie.syncCrazyflie import SyncCrazyflie

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    'test_setup',
    conftest.get_devices(),
    indirect=True,
    ids=lambda d: d.name
)
class TestParameters:
    def test_param_ronly(self, test_setup):
        with SyncCrazyflie(test_setup.device.link_uri) as scf:
            # Get a known (core) read-only parameter
            param = 'deck.bcLighthouse4'
            element = scf.cf.param.toc.get_element_by_complete_name(param)
            assert element is not None

            # Make sure it is marked as read-only
            assert element.get_readable_access() == 'RO'

            # Make sure we get an error if we try to set it
            with pytest.raises(AttributeError):
                scf.cf.param.set_value(param, 1)

    def test_param_extended_type(self, test_setup):
        with SyncCrazyflie(test_setup.device.link_uri) as scf:
            # Get a known persistent parameter
            param = 'ring.effect'
            element = scf.cf.param.toc.get_element_by_complete_name(param)
            assert element is not None
            assert element.is_extended()
            assert element.is_persistent()

            # And a known non-persistent parameter
            param = 'stabilizer.stop'
            element = scf.cf.param.toc.get_element_by_complete_name(param)
            print(element.is_persistent)
            assert element is not None
            assert not element.is_extended()
            assert not element.is_persistent()

    def test_param_persistent_store(self, test_setup):
        # Get a known persistent parameter
        param = 'sound.effect'

        # Get a random valid value
        value = random.randint(8, 13)

        with SyncCrazyflie(test_setup.device.link_uri) as scf:
            # Set Value
            logger.info(f'Setting value {value} as {param}')
            scf.cf.param.set_value(param, value)

            got_callback = False

            def store_cb(name, success):
                nonlocal got_callback
                assert name == param
                assert success

                got_callback = True

            scf.cf.param.persistent_store(param, store_cb)
            tries = 5
            while not got_callback and tries > 0:
                time.sleep(1)
                tries -= 1
            assert got_callback

            test_setup.device.reboot()

        # Allow time to reboot
        time.sleep(5)

        with SyncCrazyflie(test_setup.device.link_uri) as scf:
            val = scf.cf.param.get_value(param)
            assert int(val) == value

    def test_param_persistent_clear(self, test_setup):
        with SyncCrazyflie(test_setup.device.link_uri) as scf:
            # Get a known persistent parameter
            param = 'sound.effect'

            gotten_state = False

            def clear_cb(name, success):
                assert name == param
                assert success

            def state_cb_1(name, state):
                nonlocal gotten_state

                assert name == param

                assert state is not None
                assert isinstance(state.is_stored, bool)
                assert state.default_value == 0
                if state.is_stored:
                    scf.cf.param.persistent_clear(param, clear_cb)
                    assert state.stored_value is not None
                else:
                    assert state.stored_value is None

                gotten_state = True

            scf.cf.param.persistent_get_state(param, state_cb_1)
            tries = 5
            while not gotten_state and tries > 0:
                time.sleep(1)
                tries -= 1
            assert gotten_state

            # Allow time to reboot
            time.sleep(5)
            gotten_state = False

            def state_cb_2(name, state):
                nonlocal gotten_state

                assert name == param
                assert state is not None
                assert isinstance(state.is_stored, bool)
                assert not state.is_stored
                gotten_state = True

            scf.cf.param.persistent_get_state(param, state_cb_2)
            tries = 5
            while not gotten_state and tries > 0:
                time.sleep(1)
                tries -= 1
            assert gotten_state

    def test_param_persistent_get_state(self, test_setup):
        with SyncCrazyflie(test_setup.device.link_uri) as scf:
            # Get a known persistent parameter
            param = 'sound.effect'

            gotten_state = False

            def state_cb(name, state):
                nonlocal gotten_state

                assert name == param
                assert state is not None
                logger.info(f'state: {state}')
                assert isinstance(state.is_stored, bool)
                assert state.default_value == 0
                if state.is_stored:
                    assert state.stored_value is not None
                else:
                    assert state.stored_value is None

                gotten_state = True

            scf.cf.param.persistent_get_state(param, state_cb)
            tries = 5
            while not gotten_state and tries > 0:
                time.sleep(1)
                tries -= 1
            assert gotten_state

            # Attempt to get state from non-persistent param,
            # make sure we get AttributeError.
            param = "stabilizer.stop"
            with pytest.raises(AttributeError):
                scf.cf.param.persistent_get_state(param, state_cb)

    def test_param_set_raw(self, test_setup):
        param = 'ring.effect'
        value = 13  # Gravity effect
        updated = False

        def param_raw_cb(name: str, val: str):
            nonlocal param
            nonlocal value
            nonlocal updated

            assert name == param
            assert value == int(val)
            updated = True

        with SyncCrazyflie(test_setup.device.link_uri) as scf:
            [group, name] = param.split('.')

            scf.wait_for_params()

            # 0x08 = UINT_8,
            scf.cf.param.add_update_callback(
                group=group,
                name=name,
                cb=param_raw_cb
            )
            scf.cf.param.set_value_raw(param, 0x08, value)
            scf.cf.param.request_param_update(param)

            tries = 5
            while not updated and tries > 0:
                time.sleep(1)
                tries -= 1

            assert updated

    def test_param_set(self, test_setup):
        param = 'stabilizer.estimator'

        def param_cb(name: str, value: str):
            nonlocal expected
            nonlocal param

            assert name == param
            assert expected.pop(0) == int(value)

        with SyncCrazyflie(test_setup.device.link_uri) as scf:
            [group, name] = param.split('.')

            initial = scf.cf.param.get_value(param)
            assert initial is not None

            expected = [2, 1, 2, 1, int(initial)]

            scf.cf.param.add_update_callback(
                group=group,
                name=name,
                cb=param_cb
            )

            scf.cf.param.set_value(param, 2)
            scf.cf.param.set_value(param, 1)
            scf.cf.param.set_value(param, 2)
            scf.cf.param.set_value(param, 1)

            scf.cf.param.set_value(param, int(initial))

            timeout = 5  # seconds
            time.sleep(timeout)

            assert len(expected) == 0
