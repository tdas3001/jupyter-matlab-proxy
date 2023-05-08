# Copyright 2023 The MathWorks, Inc.

import os
import sys
import unittest

from matlab_kernel_tests import MATLABKernelTests


class TestMATLABIntegration(MATLABKernelTests):
    """Test class for integration testing of Jupyter Notebook integration
    in presence of MATLAB"""

    def test_matlab_kernel_stderr(self):
        """Validates if MATLAB Kernel errors out correctly"""

        reply, output_msgs = self.run_code(code='error("expected error")')
        self.assertEqual(
            self.get_output_header_msg_type(output_msgs),
            "stream",
            f"The output is:\n{self.get_output(output_msgs)}",
        )
        self.assertEqual(self.get_output_msg_name(output_msgs), "stderr")
        self.assertEqual(self.get_output(output_msgs), "expected error")

    def test_matlab_kernel_ver(self):
        """Validates if 'ver' command executes successfully in MATLAB Kernel"""

        reply, output_msgs = self.run_code(code="ver", timeout=10)
        self.assertEqual(self.get_output_header_msg_type(output_msgs), "stream")
        self.assertEqual(
            self.get_output_msg_name(output_msgs),
            "stdout",
            f"The output is:\n{self.get_output(output_msgs)}",
        )
        self.assertIn("MATLAB", self.get_output(output_msgs))

    def test_matlab_kernel_simple_addition(self):
        """Validates if 'TestSimpleAddition' MATLAB test file executes without any failures"""
        test_filepath = os.path.join(os.path.dirname(__file__), "TestSimpleAddition.m")
        self.validate_matlab_test(test_filepath)


if __name__ == "__main__":
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    runner = unittest.TextTestRunner(verbosity=2)
    suite.addTest(loader.loadTestsFromTestCase(TestMATLABIntegration))
    result = runner.run(suite)
    sys.exit(not result.wasSuccessful())
