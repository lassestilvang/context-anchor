import unittest
import shutil
import logging
from pathlib import Path
from src.contextanchor.logging import setup_logging, get_logger
from src.contextanchor.errors import NetworkError, ContextAnchorError


class TestLoggingAndErrors(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("tests/tmp_logs")
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(parents=True)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

        # Reset logging to avoid side effects
        logger = logging.getLogger("contextanchor")
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    def test_setup_logging_creates_file(self):
        setup_logging(self.test_dir)
        logger = get_logger("test")
        logger.info("Test message")

        log_file = self.test_dir / "logs" / "contextanchor.log"
        self.assertTrue(log_file.exists())
        with open(log_file, "r") as f:
            content = f.read()
            self.assertIn("Test message", content)
            self.assertIn("contextanchor.test", content)

    def test_log_rotation(self):
        setup_logging(self.test_dir)

        # Write enough to trigger rotation (maxBytes=10*1024*1024, but let's assume we can't wait for that)
        # Instead, we just verify the handler is a RotatingFileHandler
        root_logger = logging.getLogger("contextanchor")
        from logging.handlers import RotatingFileHandler

        has_rotating = any(isinstance(h, RotatingFileHandler) for h in root_logger.handlers)
        self.assertTrue(has_rotating)

    def test_error_hierarchy(self):
        error = NetworkError("Timeout")
        self.assertIsInstance(error, ContextAnchorError)
        self.assertIsInstance(error, Exception)


if __name__ == "__main__":
    unittest.main()
