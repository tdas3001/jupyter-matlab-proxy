# Integration Testing of jupyter-matlab-proxy

## Testing with real MATLAB in the loop

These tests validate if the Jupyter Notebook Integration works well in presence of a real MATLAB. It covers running code in a jupyter notebook cell in an automated way without involving the UI.

### Test Requirements
1. MATLAB (Version > `R2020b`) in the system path
2. `pytest` and `jupyter-kernel-test` python packages
3. MATLAB Proxy requirements
4. Jupyter MATLAB Proxy requirements
### Test Setup
We use [jupyter-kernel-test](https://github.com/jupyter/jupyter_kernel_test) python package and [unittest](https://docs.python.org/3/library/unittest.html) test framework to support our tests. While launching Jupyter, the `setup-matlab` entrypoint is triggered which launches matlab-proxy process in jupyter server. The `jupyter-matlab-kernel` then searches for any running matlab-proxy processes in jupyter server using `jupyter-matlab-kernel/kernel::start_matlab_proxy` function. Once it finds a process, it starts using it to talk to MATLAB.

Now, the package `jupyter-kernel-test`, unfortunately, only considers MATLAB Kernel as the SUT and does not look into the Jupyter server for running matlab-proxy processes. So, we bypass the jupyter server in our tests and establish a direct link between `jupyter-matlab-proxy` and `matlab-proxy`. We do this by starting an asynchronous matlab-proxy server in test setup and then passing the server configurations such as app port, base url etc. as environment variables to the MATLAB Kernel, so it can use this server to serve MATLAB. We add a test endpoint to the `start_matlab_proxy` function of `jupyter-matlab-kernel/kernel.py` to use the matlab-proxy configurations provided by the tests instead of looking into the jupyter server for a running matlab-proxy process.

### Test Execution
1. These tests check the basic standard stuff a jupyter kernel should support such as kernel info, printing a message, running code, tab completion etc.
2. They also check some aspects specific to MATLAB Kernel such as running `ver` command, MATLAB test file, plotting MATLAB figures etc.

### Test Teardown
After the test execution ends, the matlab-proxy process is terminated and all the environment variables set for testing purposes are unset to restore the system to the original state.