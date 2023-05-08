% Copyright 2023 The MathWorks, Inc.

classdef TestSimpleAddition < matlab.unittest.TestCase

    methods (Test)
        function testSimpleAddition(testCase)
            % Test case for a simple addition

            % Input arguments
            a = 2;
            b = 3;

            % Expected output
            expected = 5;

            % Actual output
            actual = a + b;

            % Verify the output
            testCase.verifyEqual(actual, expected);
        end
    end
end