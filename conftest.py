import pytest


def pytest_addoption(parser):
    parser.addoption("--docker-image", action="store", default="testq2dataflow")



@pytest.fixture(scope="session")
def docker_image(pytestconfig):
    return pytestconfig.getoption('docker_image')
