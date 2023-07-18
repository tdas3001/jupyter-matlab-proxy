# Copyright 2023 The MathWorks, Inc.

import integration_test_utils
import pytest
import requests


@pytest.fixture(autouse=True, scope="module")
def monkeypatch_module_scope(request):
    """
    Pytest fixture for creating a monkeypatch object in 'module' scope.
    The default monkeypatch fixture returns monkeypatch object in
    'function' scope but a 'module' scope object is needed with matlab-proxy
    'module' scope fixture.

    Args:
        request (fixture): built-in pytest fixture

    Yields:
        class object: Object of class MonkeyPatch
    """
    # Importing monkeypatch here to avoid importing it at the module level
    from _pytest.monkeypatch import MonkeyPatch

    monkeypatch = MonkeyPatch()

    yield monkeypatch

    def fin():
        monkeypatch.undo()

    request.addfinalizer(fin)


@pytest.fixture(autouse=True, scope="module")
def matlab_proxy_fixture(monkeypatch_module_scope):
    """
    Pytest fixture for managing a standalone matlab-proxy process
    for testing purposes. This fixture sets up a matlab-proxy process in
    the module scope, and tears it down after all the tests are executed.

    Args:
        monkeypatch_module_scope (fixture): returns a MonkeyPatch object
        available in module scope
    """
    import matlab_proxy.util

    integration_test_utils.perform_basic_checks()

    # Select a random free port to serve matlab-proxy for testing
    mwi_app_port = integration_test_utils.get_random_free_port()
    mwi_base_url = "/matlab-test"

    # '127.0.0.1' is used instead 'localhost' for testing since Windows machines consume
    # some time to resolve 'localhost' hostname
    matlab_proxy_url = f"http://127.0.0.1:{mwi_app_port}{mwi_base_url}"

    # Start matlab-proxy-app for testing
    input_env = {
        # MWI_JUPYTER_TEST env variable is used in jupyter_matlab_kerenl/kernel.py
        # to bypass jupyter server for testing
        "MWI_JUPYTER_TEST": "true",
        "MWI_APP_PORT": mwi_app_port,
        "MWI_BASE_URL": mwi_base_url,
    }

    # Get event loop to start matlab-proxy in background
    loop = matlab_proxy.util.get_event_loop()

    # Run matlab-proxy in the background in an event loop
    proc = loop.run_until_complete(
        integration_test_utils.start_matlab_proxy_app(input_env=input_env)
    )
    # Setup matlab-proxy for testing
    __setup_matlab_proxy(matlab_proxy_url)

    # Update the OS environment variables such as app port, base url etc.
    # so that they can be used by MATLAB Kernel to obtain MATLAB
    for key, value in input_env.items():
        monkeypatch_module_scope.setenv(key, value)

    # Run the jupyter kernel tests
    yield

    # Teardown matlab-proxy for testing
    __teardown_matlab_proxy(matlab_proxy_url)

    # Terminate matlab-proxy
    proc.terminate()
    loop.run_until_complete(proc.wait())


def __setup_matlab_proxy(matlab_proxy_url):
    """
    Function to set up matlab-proxy

    Args:
        matlab_proxy_url (string): URL to access matlab-proxy
    """
    import polling

    # Poll for matlab-proxy URL to respond
    polling.poll(
        lambda: requests.get(matlab_proxy_url, verify=False).status_code == 200,
        step=5,
        timeout=120,
        ignore_exceptions=(
            requests.exceptions.ConnectionError,
            requests.exceptions.SSLError,
        ),
    )
    # License matlab-proxy using playwright UI automation
    integration_test_utils.license_matlab_proxy(matlab_proxy_url)

    # Wait for matlab-proxy to be up and running
    integration_test_utils.wait_matlab_proxy_up(matlab_proxy_url)


def __teardown_matlab_proxy(matlab_proxy_url):
    """
    Function to tear down matlab-proxy

    Args:
        matlab_proxy_url (string): URL to access matlab-proxy
    """
    # Unlicense matlab-proxy
    integration_test_utils.unlicense_matlab_proxy(matlab_proxy_url)
