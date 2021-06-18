# crazyflie-testing
Tests and infrastructure for testing Bitcraze devices in a physical lab.

## Requirements
The tests defined in the QA suite (`tests/QA`) all reference requirements found
in the `requirements/` folder. The requiremens are written in `TOML` and are
parsed by the test suite in a way that the tests can reference limits in the
tests.

## Sites
Before running the test suite you need to define a site in the `sites/` folder.
The site `TOML` tells the test suite which devices to tests, what capabilities
and decks they have, and how to reach them.

See the file `sites/single-cf.toml` for the site file format to define new test sites.
## Running the test

To run the test for a single Crazyflie, run:
```
CRAZY_SITE=single-cf pytest --verbose
```

If you have defined your own site, then change the `CRAZY_SITE` environment
variable to reflect that.

## Management
There are some scripts in the `management/` folder to help manage the devices
in your site.

```
management/program.py               - Flash a firmware file to devices in site
management/bootloader_addresses.py  - List all devices bootloader addresses
```