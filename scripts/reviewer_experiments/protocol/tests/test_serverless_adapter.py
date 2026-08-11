from __future__ import annotations

import sys
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.serverless_adapter import (
    _server_environment,
)


class ServerEnvironmentTests(unittest.TestCase):
    def test_rust_python_helper_is_pinned_to_adapter_interpreter(self) -> None:
        environment, interpreter = _server_environment()

        self.assertEqual(interpreter, Path(sys.executable).resolve())
        self.assertEqual(environment["SERVERLESS_SIM_PYTHON"], str(interpreter))
        self.assertEqual(environment["SERVERLESS_SIM_LOG_LEVEL"], "warn")
        self.assertTrue(interpreter.is_file())


if __name__ == "__main__":
    unittest.main()
