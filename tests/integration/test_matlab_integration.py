# Copyright 2023 The MathWorks, Inc.

import asyncio
import os

import jupyter_kernel_test
import tests.integration.utils as utils


class MATLABKernelTests(jupyter_kernel_test.KernelTests):
    """Base Class for MATLAB Kernel testing with jupyter-kernel-test package"""

    # The name identifying an installed kernel to run the tests against
    kernel_name = "jupyter_matlab_kernel"

    # language_info.name in a kernel_info_reply should match this
    language_name = "matlab"

    # Throws error in cell output
    code_stderr = "error('expected error')"

    # Prints message in cell output
    code_hello_world = "disp('hello, world')"

    # Executes code and validates output
    code_execute_result = [{"code": "a = 1;a = a + 1", "result": "a = \n   2"}]

    # Tests tab completion
    completion_samples = [
        {
            "text": "func",
            "matches": [
                "func2str",
                "function",
                "function_handle",
                "functionhintsfunc",
                "functions",
                "functiontests",
            ],
        }
    ]

    # Clears the cell output area
    code_clear_output = "clc"

    @classmethod
    def setUpClass(cls):
        import matlab_proxy.util
        import matlab_proxy.settings

        # Get event loop to start matlab-proxy in background
        cls.loop = matlab_proxy.util.get_event_loop()

        # Validate MATLAB before testing
        matlab_path = matlab_proxy.settings.get_matlab_path()
        assert matlab_path is not None, "MATLAB is not in system path"
        assert (
            matlab_proxy.settings.get_matlab_version(matlab_path) > "R2020b"
        ), "MATLAB version should be above R2022b"

        # # Store the matlab proxy logs in os.pipe for testing
        # os.pipe2 is not supported in Mac and Windows systems
        from matlab_proxy.util import system

        cls.dpipe = os.pipe2(os.O_NONBLOCK) if system.is_linux() else os.pipe()

        # Select a random free port to serve matlab proxy for testing
        cls.mwi_app_port = utils.get_random_free_port()
        cls.mwi_base_url = "/matlab-test"

        # Environment variables to launch matlab proxy
        cls.input_env = {
            "MWI_JUPYTER_TEST": "true",
            "MWI_APP_PORT": cls.mwi_app_port,
            "MWI_BASE_URL": cls.mwi_base_url,
        }

        # Start matlab-proxy-app
        cls.proc = cls.loop.run_until_complete(
            utils.start_matlab_proxy_app(out=cls.dpipe[1], input_env=cls.input_env)
        )
        # Wait for matlab-proxy to be up and running
        utils.wait_matlab_proxy_up(cls.mwi_app_port, cls.mwi_base_url)

        # Update the OS environment variables such as app port, base url etc.
        # so that they can be used by MATLAB Kernel to obtain MATLAB
        os.environ.update(cls.input_env)
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

    def test_completion(self):
        """MATLAB Kernel implementation of tab completion test method"""
        input_text = "func"
        msg_id = self.kc.complete(input_text)
        reply = self.get_non_kernel_info_reply()
        jupyter_kernel_test.validate_message(reply, "complete_reply", msg_id)
        matches = set(reply["content"]["matches"])
        self.assertGreater(
            len(matches), 0, f"The text '{input_text}' does not have any tab completion"
        )
        for element in matches:
            with self.subTest(element=element):
                assert element.startswith(
                    input_text
                ), f"The element '{element}' in tab completion list does not start with '{input_text}'"

    def test_matlab_kernel_ver(self):
        """Validates if 'ver' command executes successfully in MATLAB Kernel"""

        reply, output_msgs = self.run_code(code="ver")
        self.assertEqual(self.get_output_header_msg_type(output_msgs), "stream")
        self.assertEqual(
            self.get_output_msg_name(output_msgs),
            "stdout",
            f"The output is:\n{self.get_output_text(output_msgs)}",
        )
        self.assertIn("MATLAB", self.get_output_text(output_msgs))

    def test_matlab_kernel_simple_addition(self):
        """Validates if 'TestSimpleAddition' MATLAB test file executes without any failures"""

        test_filepath = os.path.join(os.path.dirname(__file__), "TestSimpleAddition.m")
        self.validate_matlab_test(test_filepath)

    def test_matlab_kernel_peaks(self):
        """Validates if 'peaks' command plots a figure in jupyter cell output"""

        reply, output_msgs = self.run_code(code="peaks")
        self.assertEqual(
            self.get_output_header_msg_type(output_msgs),
            "execute_result",
            f"The expected output header is 'execute_result'",
        )
        self.assertIn(
            "image/png",
            output_msgs[-1]["content"]["data"],
            "No figure was generated in output",
        )

    # ---- Utility Functions ----
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

    def get_output_text(self, output_msgs):
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
            self.get_output_text(output_msgs),
        )
        self.assertIn("0 Failed, 0 Incomplete", self.get_output_text(output_msgs))
