from contextanchor.git_observer import GitObserver


class TestGitHubEnrichment:
    def test_parse_references(self):
        obs = GitObserver()

        # Test basic parsing
        text = "Fixes #123 and GH-456. Also see #789."
        refs = obs.parse_references(text)
        assert 123 in refs["issue_references"]
        assert 456 in refs["issue_references"]
        assert 789 in refs["issue_references"]

        # Test PR specifically
        text = "Merge pull request #1011 from some-branch"
        refs = obs.parse_references(text)
        assert 1011 in refs["pr_references"]

    def test_github_metadata_extraction(self, mocker):
        obs = GitObserver()

        # HTTPS
        mocker.patch.object(obs, "get_remote_url", return_value="https://github.com/owner/repo.git")
        meta = obs.get_github_metadata()
        assert meta.owner == "owner"
        assert meta.name == "repo"

        # SSH
        mocker.patch.object(obs, "get_remote_url", return_value="git@github.com:user/project.git")
        meta = obs.get_github_metadata()
        assert meta.owner == "user"
        assert meta.name == "project"

        # Non-GitHub
        mocker.patch.object(obs, "get_remote_url", return_value="https://gitlab.com/owner/repo.git")
        meta = obs.get_github_metadata()
        assert meta is None
