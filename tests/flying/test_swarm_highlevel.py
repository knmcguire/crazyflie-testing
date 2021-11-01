
import time
import conftest
import pytest
import logging

from collections import defaultdict
from collections import namedtuple

from cflib.crazyflie.log import LogConfig

logging.disable(logging.CRITICAL)

State = namedtuple('State', 'x y z isTumbled isFlying isCharging battery')

LANDING_ATTEMPTS = 5
NUMBER_OF_ITERATIONS = 50


class SwarmManager:
    def __init__(self):
        print('get swarm')
        self.swarm = conftest.get_swarm()
        self.swarm.open_links()
        self.states = dict()
        self._is_charging = defaultdict(lambda: False)

        print('start_state_logging')
        self.swarm.parallel_safe(self.start_state_logging)
        self.swarm.parallel_safe(lambda scf: scf.cf.param.set_value('commander.enHighLevel', 1))
        # self.swarm.parallel_safe(lambda scf: scf.cf.param.set_value('sys.disconnectedFlight', 1))

    def takeoff(self):
        self.swarm.parallel_safe(self._takeoff)

    def land_and_charge(self, positions):
        parameters = {key: [value] for (key, value) in positions.items()}
        self.swarm.parallel_safe(self._land_and_charge, args_dict=parameters)

    def _takeoff(self, scf):
        for _ in range(5):
            scf.cf.high_level_commander.takeoff(0.6, 2)
        time.sleep(3)

    def _land(self, scf, pos):
        for _ in range(5):
            scf.cf.high_level_commander.go_to(pos.x, pos.y, 0.1, 0, 5)
        time.sleep(6)

        for _ in range(5):
            scf.cf.high_level_commander.land(0, 1.0)
        time.sleep(1.5)

    def _land_and_charge(self, scf, pos):
        if not self.states[scf.cf.link_uri].isFlying:
            return

        attempts = 0
        while True:
            self._land(scf, pos)
            time.sleep(2)

            if self.states[scf.cf.link_uri].isCharging:
                return

            print(f'{scf.cf.link_uri}: Charging not detected, retry ...')

            attempts = attempts + 1
            assert attempts < LANDING_ATTEMPTS

            self._takeoff(scf)

    def ok_to_fly(self):
        for uri, state in self.states.items():
            print(f'{uri}: {state}')
            if state.isTumbled:
                print(f'{uri} is tumbled!')
                return False
        return True

    def _get_battery_limit(self, uri):
        if self._is_charging[uri]:
            return 3.9
        else:
            return 3.8

    def charge_ok(self):
        for uri, state in self.states.items():
            if state.battery < self._get_battery_limit(uri):
                self._is_charging[uri] = True
                print(f'{uri} has battery below limit ({state.battery}), waiting ...')
                return False
            else:
                print(f'{uri} - battery level {state.battery}: Ok!')
                self._is_charging[uri] = False

        return True

    def _state_logging_cb(self, ts, data, config):
        self.states[config.name] = State(
            data['stateEstimate.x'],
            data['stateEstimate.y'],
            data['stateEstimate.z'],
            data['sys.isTumbled'],
            data['sys.isFlying'],
            data['pm.state'] == 1,
            data['pm.vbat'],
        )
        state = self.states[config.name]
        self._fp.write(f'{config.name}, {ts}, {state.x}, {state.y}, {state.z}\n')

    def start_state_logging(self, scf):
        print(f'{scf.cf.link_uri}: start_state_logging')
        self._fp = open('testlog.csv', 'w')

        config = LogConfig(name=scf.cf.link_uri, period_in_ms=500)
        config.add_variable('stateEstimate.x', 'float')
        config.add_variable('stateEstimate.y', 'float')
        config.add_variable('stateEstimate.z', 'float')

        config.add_variable('sys.isFlying', 'uint8_t')
        config.add_variable('sys.isTumbled', 'uint8_t')

        config.add_variable('pm.state', 'uint8_t')
        config.add_variable('pm.vbat', 'float')

        scf.cf.log.add_config(config)
        config.data_received_cb.add_callback(self._state_logging_cb)
        config.start()


@pytest.fixture(name='swarm_manager', scope='function')
def swarm_manager_fixture():
    return SwarmManager()


def test_swarm_highlevel_takeoff(swarm_manager):
    logger = logging.getLogger()
    logger.disabled = True

    print('\n')
    print('Reset estimators ...')
    swarm_manager.swarm.reset_estimators()

    iterations = 0
    while swarm_manager.ok_to_fly() and iterations < NUMBER_OF_ITERATIONS:
        should_break = False

        if not swarm_manager.charge_ok():
            time.sleep(15)
            continue

        iterations += 1
        print(f'Iteration #{iterations}')

        print('Getting estimated positions ...')
        positions = swarm_manager.swarm.get_estimated_positions()

        print('Takeoff ...')
        swarm_manager.takeoff()

        time.sleep(2)

        for uri, state in swarm_manager.states.items():
            if not state.isFlying:
                print(f'{uri} is not flying!')
                should_break = True

        print('Land ...')
        swarm_manager.land_and_charge(positions)

        if should_break:
            break

        time.sleep(30)

    swarm_manager.swarm.close_links()
