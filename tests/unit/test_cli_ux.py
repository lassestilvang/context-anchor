import unittest
from pathlib import Path
import shutil
import os
from unittest.mock import patch
from click.testing import CliRunner
from src.contextanchor.cli import _find_git_root, main


class TestCLIUX(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.test_repo = Path.cwd().absolute() / "tests" / "tmp_ux_repo"
        if self.test_repo.exists():
            shutil.rmtree(self.test_repo)
        self.test_repo.mkdir(parents=True)
        # Create a dummy .git dir and hooks dir
        (self.test_repo / ".git" / "hooks").mkdir(parents=True)

    def tearDown(self):
        if self.test_repo.exists():
            shutil.rmtree(self.test_repo)

    def test_find_git_root_from_subdirectory(self):
        sub = self.test_repo / "a" / "b" / "c"
        sub.mkdir(parents=True)

        # Change CWD to sub
        old_cwd = os.getcwd()
        os.chdir(sub)
        try:
            # We must resolve test_repo BEFORE chdir or use the absolute path we stored
            root = _find_git_root()
            self.assertEqual(Path(root).resolve(), self.test_repo.resolve())
        finally:
            os.chdir(old_cwd)

    @patch("src.contextanchor.cli.console")
    @patch("src.contextanchor.cli._find_git_root")
    @patch("src.contextanchor.cli._install_git_hook")
    def test_init_success_styling(self, mock_hook, mock_find_root, mock_console):
        mock_find_root.return_value = self.test_repo
        mock_hook.return_value = "active"

        # Ensure config doesn't exist
        config_path = self.test_repo / ".contextanchor" / "config.yaml"
        if config_path.exists():
            shutil.rmtree(config_path.parent)

        result = self.runner.invoke(main, ["init"])

        if result.exit_code != 0:
            print(f"DEBUG Output: {result.output}")
            if result.exception:
                import traceback

                traceback.print_exception(
                    type(result.exception), result.exception, result.exception.__traceback__
                )

        self.assertEqual(result.exit_code, 0)
        # Verify rich console was used for success message
        mock_console.print.assert_any_call(
            "[success]✅ ContextAnchor initialized successfully![/success]"
        )

    @patch("src.contextanchor.cli.console")
    @patch("src.contextanchor.cli._find_git_root")
    def test_init_outside_repo(self, mock_find_root, mock_console):
        mock_find_root.return_value = None

        result = self.runner.invoke(main, ["init"])

        self.assertNotEqual(result.exit_code, 0)
        mock_console.print.assert_any_call("[error]❌ Error: Not inside a git repository.[/error]")


if __name__ == "__main__":
    unittest.main()
