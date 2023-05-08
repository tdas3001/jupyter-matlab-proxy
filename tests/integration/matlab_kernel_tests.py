# Copyright 2023 The MathWorks, Inc.

import asyncio
import json
import os
import socket
import time

import jupyter_kernel_test
import urllib3


def matlab_cmd_for_testing():
    """Returns command for starting matlab-proxy process"""

    import matlab_proxy

    from jupyter_matlab_proxy.jupyter_config import config

    matlab_cmd = [
        matlab_proxy.get_executable_name(),
        "--config",
        config["extension_name"],
    ]
    return matlab_cmd


class MATLABKernelTests(jupyter_kernel_test.KernelTests):
    """Base Class for MATLAB Kernel testing with jupyter-kernel-test package"""

    # The name identifying an installed kernel to run the tests against
    kernel_name = "jupyter_matlab_kernel"

    # language_info.name in a kernel_info_reply should match this
    language_name = "matlab"

    @classmethod
    def setUpClass(cls):
        cls.loop = asyncio.get_event_loop()

        # # Store the matlab proxy logs in os.pipe for testing
        # os.pipe2 is not supported in Mac and Windows systems
        from matlab_proxy.util import system

        cls.dpipe = os.pipe2(os.O_NONBLOCK) if system.is_linux() else os.pipe()

        # Select a random free port to serve matlab proxy for testing
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("", 0))
        cls.mwi_app_port = str(s.getsockname()[1])
        cls.mwi_base_url = "/matlab-test/"
        s.close()

        # Environment variables to launch matlab proxy
        cls.input_env = {
            "MWI_JUPYTER_TEST": "true",
            "MWI_APP_PORT": cls.mwi_app_port,
            "MWI_BASE_URL": cls.mwi_base_url,
        }

        async def start_matlab_proxy_app(out=asyncio.subprocess.PIPE, input_env={}):
            """Starts MATLAB proxy as a subprocess
            Returns the subprocess object"""

            cmd = matlab_cmd_for_testing()
            matlab_proxy_env = os.environ.copy()
            input_env_copy = input_env.copy()
            input_env_copy["MWI_BASE_URL"] += "matlab"
            matlab_proxy_env.update(input_env_copy)
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                env=matlab_proxy_env,
                stdout=out,
                stderr=out,
            )
            return proc

        def wait_matlab_proxy_up(mwi_app_port, mwi_base_url):
            """Wait for matlab-proxy to be up and running"""

            from matlab_proxy.util import system

            # TImeout for polling the matlab-proxy http endpoints
            # matlab proxy in Mac machines takes more time to be 'up'
            MAX_TIMEOUT = 120 if system.is_linux() else 300

            def send_http_request(
                mwi_app_port, mwi_base_url, http_endpoint, method="GET", headers={}
            ):
                """Sens HTTP request to the matlab-proxy server"""
                uri = f"http://localhost:{mwi_app_port}{mwi_base_url}/{http_endpoint}"

                with urllib3.PoolManager(
                    retries=urllib3.Retry(backoff_factor=0.1)
                ) as http:
                    res = http.request(method, uri, fields=headers)
                    return json.loads(res.data.decode("utf-8"))

            matlab_status = "down"
            start_time = time.time()
            while matlab_status in ["down", "starting"] and (
                time.time() - start_time < MAX_TIMEOUT
            ):
                time.sleep(1)
                res = send_http_request(
                    mwi_app_port=mwi_app_port,
                    mwi_base_url=mwi_base_url+"matlab",
                    http_endpoint="get_status",
                    method="GET",
                )
                matlab_status = res["matlab"]["status"]
            assert (
                matlab_status == "up"
            ), "matlab-proxy process did not start successfully"

        cls.proc = cls.loop.run_until_complete(
            start_matlab_proxy_app(out=cls.dpipe[1], input_env=cls.input_env)
        )
        wait_matlab_proxy_up(cls.mwi_app_port, cls.mwi_base_url)
        os.environ.update(cls.input_env)
        os.environ.update({"SERVER_PROCESS_ID": str(cls.proc.pid)})
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.proc.terminate()
        cls.loop.run_until_complete(cls.proc.wait())

        # Unset the environment variables based on the configuration
        for key in cls.input_env.keys():
            os.unsetenv(key)

    def setUp(self):
        self.flush_channels()

    def run_code(self, code, timeout=30):
        """Runs code in Jupyter notebook cell"""

        reply, output_msgs = self.execute_helper(code=code, timeout=timeout)
        return reply, output_msgs

    def get_output_header_msg_type(self, output_msgs):
        """Gets the Jupyter notebook cell output header message type
        Returns 'stream', 'execute_result' etc."""

        return output_msgs[-1]["header"]["msg_type"]

    def get_output_msg_name(self, output_msgs):
        """Gets the Jupyter notebook cell output message name
        Applicable for 'stream' output header
        Returns 'stdout', 'stderr' etc."""

        return output_msgs[-1]["content"]["name"]

    def get_output(self, output_msgs):
        """Gets output text of Jupyter notebook cell"""

        if self.get_output_header_msg_type(output_msgs) == "stream":
            output = [
                output_msgs[i]["content"]["text"]
                for i in range(len(output_msgs))
                if "text" in output_msgs[i]["content"]
            ]
            output = "\n".join(output)
            return output
        elif self.get_output_header_msg_type(output_msgs) == "execute_result":
            output = [
                output_msgs[i]["content"]["data"]["text/html"]
                for i in range(len(output_msgs))
                if "data" in output_msgs[i]["content"]
            ]
            output = "\n".join(output)
            return output

    def validate_matlab_test(self, test_filepath):
        """Runs MATLAB test given the test file path. Validates if all the test
        points passed."""

        reply, output_msgs = self.run_code(
            code=f"assertSuccess(runtests('{test_filepath}'))"
        )
        self.assertEqual(
            self.get_output_header_msg_type(output_msgs),
            "execute_result",
            self.get_output(output_msgs),
        )
        self.assertIn("0 Failed, 0 Incomplete", self.get_output(output_msgs))
