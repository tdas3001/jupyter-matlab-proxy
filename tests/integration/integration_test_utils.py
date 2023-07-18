# Copyright 2023 The MathWorks, Inc.
# Utility functions for integration testing of jupyter-matlab-proxy

import asyncio
import os
import socket
import time

import requests


def perform_basic_checks():
    """
    Perform basic checks for the prerequisites for starting
    matlab-proxy
    """
    import matlab_proxy.settings

    # Validate MATLAB before testing
    matlab_path = matlab_proxy.settings.get_matlab_root_path()

    # Check if MATLAB is in the system path
    assert matlab_path is not None, "MATLAB is not in system path"

    # Check if MATLAB verison is >= R2020b
    assert (
        matlab_proxy.settings.get_matlab_version(matlab_path) >= "R2020b"
    ), "MATLAB version should be R2020b or later"


def matlab_proxy_cmd_for_testing():
    """
    Get command for starting matlab-proxy process

    Returns:
        list(string): Command for starting matlab-proxy process
    """

    import matlab_proxy

    from jupyter_matlab_proxy.jupyter_config import config

    matlab_cmd = [
        matlab_proxy.get_executable_name(),
        "--config",
        config["extension_name"],
    ]
    return matlab_cmd


async def start_matlab_proxy_app(input_env={}):
    """
    Starts matlab-proxy as a subprocess. The subprocess runs forever unless
    there is any error

    Args:
        input_env (dict, optional): Environment variables to be
        initialized for the subprocess. Defaults to {}.

    Returns:
        Process: subprocess object
    """

    cmd = matlab_proxy_cmd_for_testing()
    matlab_proxy_env = os.environ.copy()
    matlab_proxy_env.update(input_env)
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        env=matlab_proxy_env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    return proc


def wait_matlab_proxy_up(matlab_proxy_url):
    """
    Wait for matlab-proxy to be up and running

    Args:
        matlab_proxy_url (string): URL to access matlab-proxy
    """

    from matlab_proxy.util import system

    from jupyter_matlab_kernel import mwi_comm_helpers

    # Timeout for polling the matlab-proxy http endpoints.
    # matlab-proxy takes more time to be 'up' in machines
    # other than Linux
    MAX_TIMEOUT = 120 if system.is_linux() else 300

    is_matlab_licensed = False
    matlab_status = "down"
    matlab_proxy_has_error = None
    start_time = time.time()

    # Poll for matlab-proxy to be up
    while matlab_status in ["down", "starting"] and (
        time.time() - start_time < MAX_TIMEOUT
    ):
        time.sleep(1)
        try:
            (
                is_matlab_licensed,
                matlab_status,
                matlab_proxy_has_error,
            ) = mwi_comm_helpers.fetch_matlab_proxy_status(
                url=matlab_proxy_url, headers={}
            )
        except:
            # The network connection can be flaky while the
            # matlab-proxy server is booting. There can also be some
            # intermediate connection errors
            pass
    assert is_matlab_licensed == True, "MATLAB is not licensed"
    assert (
        matlab_status == "up"
    ), f"matlab-proxy process did not start successfully\nError:\n{matlab_proxy_has_error}"


def get_random_free_port() -> str:
    """
    Get a random free port

    Returns:
        string: A random free port
    """

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = str(s.getsockname()[1])
    s.close()
    return port


def license_matlab_proxy(matlab_proxy_url):
    """
    Use Playwright UI automation to license matlab-proxy.
    Uses TEST_USERNAME and TEST_PASSWORD from environment variables.

    Args:
        matlab_proxy_url (string): URL to access matlab-proxy
    """
    from playwright.sync_api import sync_playwright, expect

    # These are MathWorks Account credentials to license MATLAB
    # Throws 'KeyError' if the following environment variables are not set
    TEST_USERNAME = os.environ["TEST_USERNAME"]
    TEST_PASSWORD = os.environ["TEST_PASSWORD"]

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(matlab_proxy_url)

        # Fills in the username textbox
        email_text_box = page.frame_locator("#loginframe").locator("#userId")
        expect(
            email_text_box,
            "Wait for email ID textbox to appear. This might fail if the MHLM licensing window does not appear",
        ).to_be_visible(timeout=60000)
        email_text_box.fill(TEST_USERNAME)
        email_text_box.press("Enter")

        # Fills in the password textbox
        password_text_box = page.frame_locator("#loginframe").locator("#password")
        expect(password_text_box, "Wait for password textbox to appear").to_be_visible(
            timeout=30000
        )
        password_text_box.fill(TEST_PASSWORD)
        password_text_box.press("Enter")
        password_text_box.press("Enter")

        # Verifies if licensing is successful by checking the status information
        status_info = page.get_by_text("Status Information")
        expect(
            status_info,
            "Verify if Licensing is successful. This might fail if incorrect credentials are provided",
        ).to_be_visible(timeout=60000)
        browser.close()


def unlicense_matlab_proxy(matlab_proxy_url):
    """
    Unlicense matlab-proxy that is licensed using online licensing

    Args:
        matlab_proxy_url (string): URL to access matlab-proxy
    """
    max_retries = 3  # Max retries for unlicensing matlab-proxy
    retries = 0

    while retries < max_retries:
        error = None
        try:
            resp = requests.delete(
                matlab_proxy_url + "/set_licensing_info", headers={}, verify=False
            )
            if resp.status_code == requests.codes.OK:
                data = resp.json()
                assert data["licensing"] == None, "Licensing is not unset"
                assert (
                    data["matlab"]["status"] == "down"
                ), "MATLAB is not in 'stopped' state"
                assert data["error"] == None, f"Error: {data['error']}"
                break
            else:
                resp.raise_for_status()
        except Exception as e:
            error = e
        finally:
            retries += 1

    # If the above code threw error even after maximum retries, then raise error
    if error:
        raise error
