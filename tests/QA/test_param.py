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

from cflib.crazyflie.syncCrazyflie import SyncCrazyflie

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    'test_setup',
    conftest.get_devices(),
    indirect=['test_setup'],
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

    def test_param_set(self, test_setup):
        param = 'stabilizer.estimator'

        def param_cb(name: str, value: str):
            nonlocal expected
            nonlocal param

            assert name == param
            assert expected.pop(0) == int(value)

        with SyncCrazyflie(test_setup.device.link_uri) as scf:
            [group, name] = param.split('.')

            # Work-around to make sure parameter values are updated
            # will not be needed when we land code to do this automatic
            time.sleep(3)

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
