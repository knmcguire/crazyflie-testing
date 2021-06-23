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


@pytest.mark.parametrize(
    'test_setup',
    conftest.get_devices(),
    indirect=['test_setup'],
    ids=lambda d: d.name
)
class TestDecks:

    def test_deck_present(self, test_setup):
        '''
        Check that all decks defined in for the device in the site
        is detected, using the parameter interface.
        '''
        if not test_setup.device.decks:
            pytest.skip('no decks on device')

        discovered = list()

        def deck_param_callback(name, value):
            nonlocal discovered

            if int(value) == 1:
                discovered.append(name.rsplit('.')[-1])  # deck.name => name

        assert test_setup.device.connect_sync()

        test_setup.device.cf.param.add_update_callback(
            group='deck',
            name=None,
            cb=deck_param_callback
        )

        time.sleep(1)

        for deck in test_setup.device.decks:
            assert deck in discovered
