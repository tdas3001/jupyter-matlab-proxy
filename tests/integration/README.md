# Integration Testing of jupyter-matlab-proxy

## Testing with real MATLAB in the loop

These tests validate if the Jupyter Notebook Integration works well in presence of a real MATLAB. It covers running code in a jupyter notebook cell in an automated way without involving the UI.

### Test Requirements
1. MATLAB (Version > `R2020b`) in the system path
2. `pytest` and `jupyter-kernel-test` python packages
3. MATLAB Proxy requirements
4. Jupyter MATLAB Proxy requirements
### Test Setup
We use the [jupyter-kernel-test](https://github.com/jupyter/jupyter_kernel_test) python package and the [unittest](https://docs.python.org/3/library/unittest.html) testing framework in our tests.

The package `jupyter-kernel-test`, unfortunately, only considers the MATLAB Kernel as the system under test and does communicate with [Jupyter Server](https://github.com/jupyter-server/jupyter_server) to query for running matlab-proxy processes. So, we must bypass Jupyter Server in our tests and establish a direct link between `jupyter-matlab-proxy` and `matlab-proxy`. We do this by starting an asynchronous matlab-proxy server in the test setup. The matlab-proxy configurations, such as app port, base URL etc., are passed as environment variables to the MATLAB Kernel, so it can use this server to serve MATLAB.

### Test Execution
1. These tests check the basic functionality that a jupyter kernel should support, i.e. running code, tab completion, printing a message, etc.
2. They also check some aspects specific to MATLAB Kernel, such as running the `ver` command, executing a MATLAB test file, plotting MATLAB figures etc.

### Test Teardown
After the test execution ends, the matlab-proxy process is terminated and all the environment variables set for testing purposes are unset to restore the system to the original state.