# Copyright 2023 The MathWorks, Inc.
# Utility functions for integration testing of jupyter-matlab-proxy

import asyncio
import os
import socket
import time

import requests


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


async def start_matlab_proxy_app(out=asyncio.subprocess.PIPE, input_env={}):
    """
    Starts MATLAB proxy as a subprocess. The subprocess runs forever unless
    there is any error

    Args:
        out (_type_, optional): Output mode of subprocess logs.
        Defaults to asyncio.subprocess.PIPE.
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
        stdout=out,
        stderr=asyncio.subprocess.PIPE,
    )
    return proc


async def start_licensing_matlab_proxy(out=asyncio.subprocess.PIPE, input_env={}):
    """
    Starts MATLAB proxy as a subprocess and uses playwright to license
    matlab-proxy using online licensing. The subprocess does not run forever
    here because playwright terminates matlab-proxy as soon as the licensing is done

    Args:
        out (_type_, optional): Output mode of subprocess logs.
        Defaults to asyncio.subprocess.PIPE.
        input_env (dict, optional): Environment variables to be
        initialized for the subprocess. Defaults to {}.

    Returns:
        Process: subprocess object
    """

    cmd = [
        "npx",
        "playwright",
        "test",
    ]
    matlab_proxy_env = os.environ.copy()
    matlab_proxy_env.update(input_env)
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        env=matlab_proxy_env,
        stdout=out,
        stderr=asyncio.subprocess.PIPE,
        cwd=os.path.join(os.path.dirname(__file__), "configuration"),
    )
    return proc


def wait_matlab_proxy_up(mwi_app_port, mwi_base_url):
    """
    Wait for matlab-proxy to be up and running

    Args:
        mwi_app_port (string): App port where matlab-proxy would be running
        mwi_base_url (string): Context root that matlab-proxy would use
    """

    from matlab_proxy.util import system
    from jupyter_matlab_kernel import mwi_comm_helpers

    # Timeout for polling the matlab-proxy http endpoints.
    # matlab proxy takes more time to be 'up' in machines
    # other than Linux
    MAX_TIMEOUT = 120 if system.is_linux() else 300

    is_matlab_licensed = False
    matlab_status = "down"
    matlab_proxy_has_error = None
    url = f"http://localhost:{mwi_app_port}{mwi_base_url}"
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
            ) = mwi_comm_helpers.fetch_matlab_proxy_status(url=url, headers={})
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


def unlicense_matlab_proxy(mwi_app_port, mwi_base_url):
    """Unlicense matlab-proxy that is licensed using online licensing

    Args:
        mwi_app_port (string): port where matlab-proxy runs
        mwi_base_url (string): base url for matlab-proxy
    """
    max_retries = 3 # Max retries for unlicensing matlab-proxy
    retries = 0

    url = f"http://localhost:{mwi_app_port}{mwi_base_url}"
    while (retries < max_retries):
        error = None
        try:
            resp = requests.delete(url + "/set_licensing_info", headers={}, verify=False)
            if resp.status_code == requests.codes.OK:
                data = resp.json()
                assert data["licensing"] == None, "Licensing is not unset"
                assert data["matlab"]["status"] == "down", "MATLAB is not in 'stopped' state"
                assert data["error"] == None, f"Error: {data['error']}"
                break
            else:
                resp.raise_for_status()
        except Exception as e:
            error = e
        finally:
            retries+=1

    # If the above code threw error even after maximum retries, then raise error
    if error:
        raise error