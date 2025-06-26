"""Tests for CLI module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from devcontainer_tools.cli import cli


class TestCliInit:
    """Test the init command."""

    def test_init_creates_config(self):
        """Test that init command creates a config file."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "devcontainer.common.json"

            result = runner.invoke(cli, ["init", "--common-config", str(config_path)])

            assert result.exit_code == 0
            assert config_path.exists()

            # Verify content
            config = json.loads(config_path.read_text())
            assert "features" in config
            assert "mounts" in config
            assert "customizations" in config

    def test_init_existing_file_no_overwrite(self):
        """Test init with existing file and no to overwrite."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "devcontainer.common.json"
            config_path.write_text('{"existing": "config"}')

            result = runner.invoke(cli, ["init", "--common-config", str(config_path)], input="n")

            assert result.exit_code == 0
            # File should remain unchanged
            config = json.loads(config_path.read_text())
            assert config == {"existing": "config"}

    def test_init_existing_file_with_overwrite(self):
        """Test init with existing file and yes to overwrite."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "devcontainer.common.json"
            config_path.write_text('{"existing": "config"}')

            result = runner.invoke(cli, ["init", "--common-config", str(config_path)], input="y")

            assert result.exit_code == 0
            # File should be overwritten
            config = json.loads(config_path.read_text())
            assert "features" in config

    def test_init_creates_config_directory(self):
        """Test that init command creates config directory if it doesn't exist."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / ".config"
            config_path = config_dir / "devcontainer.common.json"

            result = runner.invoke(cli, ["init", "--common-config", str(config_path)])

            assert result.exit_code == 0
            assert config_dir.exists()
            assert config_path.exists()

            # Verify content
            config = json.loads(config_path.read_text())
            assert "features" in config


class TestCliUp:
    """Test the up command."""

    @patch("devcontainer_tools.cli.subprocess.run")
    @patch("devcontainer_tools.cli.find_devcontainer_json")
    def test_up_basic(self, mock_find_config, mock_subprocess):
        """Test basic up command."""
        runner = CliRunner()

        # Mock finding no project config
        mock_find_config.return_value = None

        # Mock successful subprocess run
        mock_subprocess.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            result = runner.invoke(cli, ["up", "--workspace", str(workspace)])

            assert result.exit_code == 0
            # Verify devcontainer up was called
            mock_subprocess.assert_called_once()
            args = mock_subprocess.call_args[0][0]
            assert args[0:2] == ["devcontainer", "up"]

    @patch("devcontainer_tools.cli.subprocess.run")
    @patch("devcontainer_tools.cli.find_devcontainer_json")
    def test_up_with_options(self, mock_find_config, mock_subprocess):
        """Test up command with various options."""
        runner = CliRunner()

        mock_find_config.return_value = None
        mock_subprocess.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            result = runner.invoke(
                cli,
                [
                    "up",
                    "--workspace",
                    str(workspace),
                    "--clean",
                    "--no-cache",
                    "--gpu",
                    "--mount",
                    "/host:/container",
                    "--env",
                    "NODE_ENV=development",
                    "--port",
                    "8080",
                ],
            )

            assert result.exit_code == 0

            # Verify options were passed to devcontainer
            args = mock_subprocess.call_args[0][0]
            assert "--remove-existing-container" in args
            assert "--build-no-cache" in args
            assert "--gpu-availability" in args
            assert "all" in args

    @patch("devcontainer_tools.cli.subprocess.run")
    def test_up_failure(self, mock_subprocess):
        """Test up command when devcontainer fails."""
        runner = CliRunner()

        # Mock failed subprocess run
        mock_subprocess.return_value = MagicMock(returncode=1)

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            result = runner.invoke(cli, ["up", "--workspace", str(workspace)])

            assert result.exit_code == 1


class TestCliExec:
    """Test the exec command."""

    @patch("devcontainer_tools.cli.execute_in_container")
    def test_exec_command(self, mock_execute):
        """Test exec command."""
        runner = CliRunner()

        # Mock successful execution
        mock_execute.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            result = runner.invoke(
                cli, ["exec", "--workspace", str(workspace), "--", "bash", "-c", "echo hello"]
            )

            assert result.exit_code == 0
            mock_execute.assert_called_once_with(
                workspace, ["bash", "-c", "echo hello"], auto_up=True
            )

    @patch("devcontainer_tools.cli.execute_in_container")
    def test_exec_command_failure(self, mock_execute):
        """Test exec command when command fails."""
        runner = CliRunner()

        # Mock failed execution
        mock_execute.return_value = MagicMock(returncode=127)

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            result = runner.invoke(
                cli, ["exec", "--workspace", str(workspace), "nonexistent-command"]
            )

            assert result.exit_code == 127


class TestCliStatus:
    """Test the status command."""

    @patch("devcontainer_tools.cli.get_container_id")
    @patch("devcontainer_tools.cli.get_container_info")
    @patch("devcontainer_tools.cli.find_devcontainer_json")
    def test_status_running_container(self, mock_find_config, mock_get_info, mock_get_id):
        """Test status with running container."""
        runner = CliRunner()

        # Mock running container
        mock_get_id.return_value = "abc123container"
        mock_get_info.return_value = {
            "Config": {"Image": "test-image:latest"},
            "Mounts": [{"Source": "/host/path", "Destination": "/container/path"}],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            mock_find_config.return_value = workspace / "devcontainer.json"

            result = runner.invoke(cli, ["status", "--workspace", str(workspace)])

            assert result.exit_code == 0
            assert "Running" in result.output
            assert "abc123container"[:12] in result.output

    @patch("devcontainer_tools.cli.get_container_id")
    @patch("devcontainer_tools.cli.find_devcontainer_json")
    def test_status_no_container(self, mock_find_config, mock_get_id):
        """Test status with no running container."""
        runner = CliRunner()

        # Mock no container
        mock_get_id.return_value = None
        mock_find_config.return_value = None

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            result = runner.invoke(cli, ["status", "--workspace", str(workspace)])

            assert result.exit_code == 0
            assert "Not running" in result.output


class TestCliRebuild:
    """Test the rebuild command."""

    @patch("devcontainer_tools.cli.subprocess.run")
    @patch("devcontainer_tools.cli.find_devcontainer_json")
    def test_rebuild(self, mock_find_config, mock_subprocess):
        """Test rebuild command."""
        runner = CliRunner()

        mock_find_config.return_value = None
        mock_subprocess.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            result = runner.invoke(cli, ["rebuild", "--workspace", str(workspace)])

            assert result.exit_code == 0

            # Verify that clean and no-cache options were used
            args = mock_subprocess.call_args[0][0]
            assert "--remove-existing-container" in args
            assert "--build-no-cache" in args


class TestCliHelp:
    """Test CLI help and version."""

    def test_version(self):
        """Test version output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.0.1" in result.output

    def test_help(self):
        """Test help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "DevContainer" in result.output

    def test_command_help(self):
        """Test individual command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["up", "--help"])
        assert result.exit_code == 0
        assert "開発コンテナを起動" in result.output
