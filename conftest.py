import pytest
import os
import time
import toml
import glob

from typing import Callable
from typing import NoReturn
from typing import Optional

import cflib
from cflib.bootloader import Bootloader
from cflib.crazyflie import Crazyflie
from cflib.crtp.crtpstack import CRTPPacket
from cflib.crtp.crtpstack import CRTPPort

DIR = os.path.dirname(os.path.realpath(__file__))
SITE_PATH = os.path.join(DIR, 'sites/')
REQUIREMENT = os.path.join(DIR, 'requirements/')


class BCDevice:
    CONNECT_TIMEOUT = 10  # seconds

    def __init__(self, name, device):
        cflib.crtp.init_drivers()

        self.name = name
        self.link_uri = device['radio']
        self.cf = Crazyflie(rw_cache='./cache')
        self.bl = Bootloader(self.link_uri)

    def __str__(self):
        return '{} @ {}'.format(self.name, self.link_uri)

    def firmware_up(self) -> bool:
        ''' Return true if we can contact the (stm32 based) firmware '''
        timeout = 2  # seconds
        link = cflib.crtp.get_link_driver(self.link_uri)

        pk = CRTPPacket()
        pk.set_header(CRTPPort.LINKCTRL, 0)  # Echo channel
        pk.data = b'test'
        link.send_packet(pk)

        ts = time.time()
        while True:
            if time.time() - ts > timeout:
                break

            pk_ack = link.receive_packet(0.1)
            if pk_ack is None:
                continue

            if pk_ack.port != CRTPPort.LINKCTRL or pk_ack.channel != 0:
                continue

            if pk.data == pk_ack.data:
                link.close()
                return True

        link.close()
        return False

    def flash(self, path: str, progress_cb: Optional[Callable[[str, int], NoReturn]] = None) -> bool:
        try:
            self.bl.flash_full(cf=self.cf, filename=path, progress_cb=progress_cb, targets=[])
        except Exception as e:
            raise e
        finally:
            self.bl.close()

    def connect_sync(self, querystring=None):
        self.cf.close_link()

        if querystring is None:
            uri = self.link_uri
        else:
            uri = self.link_uri + querystring

        self.cf.open_link(uri)

        ts = time.time()
        while not self.cf.is_connected():
            time.sleep(1.0 / 1000.0)
            delta = time.time() - ts
            if delta > self.CONNECT_TIMEOUT:
                return False
        return True


class DeviceFixture:
    def __init__(self, dev: BCDevice):
        self._device = dev

    @property
    def device(self):
        return self._device


@pytest.fixture
def test_setup(request):
    ''' This code will run before (and after) a test '''
    fix = DeviceFixture(request.param)
    yield fix  # code after this point will run as teardown after test
    fix.device.cf.close_link()


def get_devices():
    devices = list()

    site = os.getenv('CRAZY_SITE')
    if site is None:
        raise Exception('No CRAZY_SITE env specified!')

    path = ""
    try:
        path = os.path.join(SITE_PATH, '%s.toml' % site)
        site_t = toml.load(open(path, 'r'))

        for name, device in site_t['device'].items():
            devices.append(BCDevice(name, device))
    except Exception:
        raise Exception('Failed to parse toml %s!' % path)

    return devices


class Requirements(dict):
    _instance = None

    def __init__(self):
        raise RuntimeError('Call instance() instead')

    @classmethod
    def _read_requirements(cls):
        requirements = glob.glob(REQUIREMENT + '*.toml')
        for requirement in requirements:
            req = toml.load(open(requirement))
            for key, value in req.items():
                if type(value) == dict:
                    if key not in cls._instance:
                        cls._instance[key] = {}
                    for subkey, subvalue in value.items():
                        cls._instance[key][subkey] = subvalue
                else:
                    cls._instance[key] = value

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
            cls._read_requirements()
        return cls._instance


def get_requirement(requirement: str):
    group, name = requirement.split('.')
    return Requirements.instance()['requirement'][group][name]
