import pytest
import conftest


@pytest.mark.parametrize('dev', conftest.get_devices(), ids=lambda d: d.name)
class TestBootloaders:

    @staticmethod
    def bootloader_back_and_forth(dev: conftest.BCDevice):
        assert dev.firmware_up()

        #
        # The start_bootloader method only returns true if it can
        # communicate with the bootloader.
        #
        assert dev.bl.start_bootloader(warm_boot=True)
        dev.bl.reset_to_firmware()
        dev.bl.close()

    def test_bootloader_reset_simple(self, dev):
        self.bootloader_back_and_forth(dev)

    def test_bootloader_reset_stress(self, dev):
        requirement = conftest.get_requirement('bootloaders', 'reliability')
        for _ in range(0, requirement['iterations']):
            self.bootloader_back_and_forth(dev)
