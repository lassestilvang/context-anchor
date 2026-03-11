from unittest.mock import patch, MagicMock
from hypothesis import given, settings, strategies as st
from click.testing import CliRunner

from src.contextanchor.cli import main, hook_branch_switch


@st.composite
def branch_names(draw):
    return draw(
        st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pd")),
            min_size=3,
            max_size=20,
        )
    )


@given(old_branch=branch_names(), new_branch=branch_names())
@settings(max_examples=20)
def test_property_fallback_branch_detection(old_branch, new_branch):
    """
    Property 17: Fallback Branch Detection
    Validates: Requirements 5.6, 5.7
    Ensures branch switch is detected and state updated when commands are invoked.
    """
    if old_branch == new_branch:
        return

    runner = CliRunner()

    with (
        patch("src.contextanchor.cli._find_git_root") as mock_find_git,
        patch("src.contextanchor.git_observer.GitObserver") as mock_git_obs_cls,
        patch("pathlib.Path.exists", return_value=True),
        patch("builtins.open") as mock_open,
        patch("src.contextanchor.api_client.APIClient"),
        patch("src.contextanchor.config.load_config"),
        patch("src.contextanchor.local_storage.LocalStorage"),
    ):
        mock_find_git.return_value = MagicMock()
        mock_git_obs = MagicMock()
        mock_git_obs.get_current_branch.return_value = new_branch
        mock_git_obs_cls.return_value = mock_git_obs

        # Mock file reading returning old_branch
        mock_file = MagicMock()
        mock_file.read.return_value = f'{{"last_branch": "{old_branch}"}}'
        mock_open.return_value.__enter__.return_value = mock_file

        result = runner.invoke(main, ["list-contexts"])

        # Verify fallback detection outputs message
        assert f"🔍 ContextAnchor: Detected switch to branch '{new_branch}'" in result.output

        # Verify it tries to save the new state
        write_calls = [c for c in mock_open.call_args_list if "w" in c[0]]
        assert len(write_calls) > 0


@given(new_branch=branch_names(), snapshot_id=st.text(min_size=5))
@settings(max_examples=20)
def test_property_primary_branch_switch_path(new_branch, snapshot_id):
    """
    Property 60: Primary Branch-Switch Detection Path
    Validates: Requirements 5.5, 5.6
    Ensures _hook-branch-switch executes and fetches right context
    """
    runner = CliRunner()
    with (
        patch("src.contextanchor.cli._find_git_root", return_value=MagicMock()),
        patch("src.contextanchor.git_observer.GitObserver") as mock_git_obs_cls,
        patch("pathlib.Path.exists", return_value=True),
        patch("builtins.open"),
        patch("src.contextanchor.api_client.APIClient") as mock_api_client_cls,
        patch("src.contextanchor.config.load_config"),
        patch("src.contextanchor.cli._render_context") as mock_render,
        patch("src.contextanchor.local_storage.LocalStorage"),
    ):
        mock_git_obs = MagicMock()
        mock_git_obs.get_current_branch.return_value = new_branch
        mock_git_obs_cls.return_value = mock_git_obs

        mock_api_client = MagicMock()
        mock_api_client.list_contexts.return_value = [{"snapshot_id": snapshot_id}]
        mock_api_client_cls.return_value = mock_api_client

        result = runner.invoke(hook_branch_switch, ["old_branch", new_branch])

        assert result.exit_code == 0
        assert f"🔍 ContextAnchor: Switched to branch '{new_branch}'" in result.output
        mock_render.assert_called_once()
