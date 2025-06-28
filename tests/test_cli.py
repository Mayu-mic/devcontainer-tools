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

    @patch("subprocess.run")
    def test_up_basic(self, mock_subprocess):
        """Test basic up command."""
        runner = CliRunner()

        # Mock successful subprocess run
        mock_subprocess.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            # Create devcontainer.json
            devcontainer_path = workspace / ".devcontainer" / "devcontainer.json"
            devcontainer_path.parent.mkdir(parents=True, exist_ok=True)
            devcontainer_path.write_text('{"name": "test"}')

            result = runner.invoke(cli, ["up", "--workspace", str(workspace)])

            assert result.exit_code == 0
            # Verify devcontainer up was called
            mock_subprocess.assert_called_once()
            args = mock_subprocess.call_args[0][0]
            assert args[0:2] == ["devcontainer", "up"]

    @patch("subprocess.run")
    def test_up_with_options(self, mock_subprocess):
        """Test up command with various options."""
        runner = CliRunner()

        mock_subprocess.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            # Create devcontainer.json
            devcontainer_path = workspace / ".devcontainer" / "devcontainer.json"
            devcontainer_path.parent.mkdir(parents=True, exist_ok=True)
            devcontainer_path.write_text('{"name": "test"}')

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

    @patch("subprocess.run")
    def test_up_failure(self, mock_subprocess):
        """Test up command when devcontainer fails."""
        runner = CliRunner()

        # Mock failed subprocess run
        mock_subprocess.return_value = MagicMock(returncode=1)

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            # Create devcontainer.json
            devcontainer_path = workspace / ".devcontainer" / "devcontainer.json"
            devcontainer_path.parent.mkdir(parents=True, exist_ok=True)
            devcontainer_path.write_text('{"name": "test"}')

            result = runner.invoke(cli, ["up", "--workspace", str(workspace)])

            assert result.exit_code == 1

    def test_up_no_devcontainer_json(self):
        """Test up command fails when no devcontainer.json exists."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            result = runner.invoke(cli, ["up", "--workspace", str(workspace)])

            assert result.exit_code == 1
            assert "devcontainer.json が見つかりません" in result.output

    @patch("subprocess.run")
    def test_up_with_devcontainer_json(self, mock_subprocess):
        """Test up command succeeds when devcontainer.json exists."""
        runner = CliRunner()
        mock_subprocess.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            # Create devcontainer.json
            devcontainer_path = workspace / ".devcontainer" / "devcontainer.json"
            devcontainer_path.parent.mkdir(parents=True, exist_ok=True)
            devcontainer_path.write_text('{"name": "test"}')

            result = runner.invoke(cli, ["up", "--workspace", str(workspace)])

            assert result.exit_code == 0
            mock_subprocess.assert_called_once()

    def test_up_dry_run_no_devcontainer_json(self):
        """Test up command with --dry-run fails when no devcontainer.json exists."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            result = runner.invoke(cli, ["up", "--workspace", str(workspace), "--dry-run"])

            assert result.exit_code == 1
            assert "devcontainer.json が見つかりません" in result.output

    def test_up_with_auto_forward_ports(self):
        """Test up command with --auto-forward-ports flag."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            # Create devcontainer.json with forwardPorts
            devcontainer_path = workspace / ".devcontainer" / "devcontainer.json"
            devcontainer_path.parent.mkdir(parents=True, exist_ok=True)
            devcontainer_path.write_text('{"name": "test", "forwardPorts": [8000, 3000]}')

            # 共通設定ファイルがないことを確認
            common_config_path = Path(temp_dir) / "common.json"

            result = runner.invoke(
                cli,
                [
                    "up",
                    "--workspace",
                    str(workspace),
                    "--dry-run",
                    "--auto-forward-ports",
                    "--common-config",
                    str(common_config_path),
                ],
            )

            assert result.exit_code == 0
            # マージ後の設定にappPortが含まれていることを確認
            assert '"appPort"' in result.output
            assert "8000" in result.output
            assert "3000" in result.output
            assert '"forwardPorts"' in result.output

    def test_up_without_auto_forward_ports(self):
        """Test up command without --auto-forward-ports flag (default behavior)."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            # Create devcontainer.json with forwardPorts
            devcontainer_path = workspace / ".devcontainer" / "devcontainer.json"
            devcontainer_path.parent.mkdir(parents=True, exist_ok=True)
            devcontainer_path.write_text('{"name": "test", "forwardPorts": [8000, 3000]}')

            # 共通設定ファイルがないことを確認
            common_config_path = Path(temp_dir) / "common.json"

            result = runner.invoke(
                cli,
                [
                    "up",
                    "--workspace",
                    str(workspace),
                    "--dry-run",
                    "--common-config",
                    str(common_config_path),
                ],
            )

            assert result.exit_code == 0
            # forwardPortsは残っているが、appPortは変換されない
            assert '"forwardPorts"' in result.output
            assert "8000" in result.output
            assert "3000" in result.output
            assert '"appPort"' not in result.output


class TestCliExec:
    """Test the exec command."""

    @patch("sys.exit")
    @patch("devcontainer_tools.container.execute_in_container")
    def test_exec_command(self, mock_execute, mock_exit):
        """Test exec command."""
        runner = CliRunner()

        # Mock successful execution
        from types import SimpleNamespace

        mock_execute.return_value = SimpleNamespace(returncode=0)

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            result = runner.invoke(
                cli, ["exec", "--workspace", str(workspace), "--", "bash", "-c", "echo hello"]
            )

            # テストアサーション
            assert result.exit_code == 0
            # execute_in_containerが正しい引数で呼び出されることを確認
            mock_execute.assert_called_once_with(
                workspace=workspace,
                command=["bash", "-c", "echo hello"],
                additional_ports=None,
                auto_up=True,
            )
            # sys.exit(0)が呼び出されることを確認
            mock_exit.assert_any_call(0)

    @patch("sys.exit")
    @patch("devcontainer_tools.container.execute_in_container")
    def test_exec_command_failure(self, mock_execute, mock_exit):
        """Test exec command when command fails."""
        runner = CliRunner()

        # Mock failed execution
        from types import SimpleNamespace

        mock_execute.return_value = SimpleNamespace(returncode=127)

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            result = runner.invoke(
                cli, ["exec", "--workspace", str(workspace), "nonexistent-command"]
            )

            assert result.exit_code == 0  # sys.exit() is mocked, so CliRunner sees success
            mock_execute.assert_called_once_with(
                workspace=workspace,
                command=["nonexistent-command"],
                additional_ports=None,
                auto_up=True,
            )
            # sys.exit(127)が呼び出されることを確認
            mock_exit.assert_any_call(127)

    @patch("sys.exit")
    @patch("devcontainer_tools.container.execute_in_container")
    def test_exec_with_port_option(self, mock_execute, mock_exit):
        """Test exec command with -p port option."""
        runner = CliRunner()

        # Mock successful execution
        from types import SimpleNamespace

        mock_execute.return_value = SimpleNamespace(returncode=0)

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            result = runner.invoke(
                cli,
                [
                    "exec",
                    "--workspace",
                    str(workspace),
                    "-p",
                    "3000:3000",
                    "-p",
                    "8080:80",
                    "--",
                    "npm",
                    "start",
                ],
            )

            assert result.exit_code == 0
            mock_execute.assert_called_once_with(
                workspace=workspace,
                command=["npm", "start"],
                additional_ports=["3000:3000", "8080:80"],
                auto_up=True,
            )
            mock_exit.assert_any_call(0)

    @patch("sys.exit")
    @patch("devcontainer_tools.container.execute_in_container")
    def test_exec_without_port_option(self, mock_execute, mock_exit):
        """Test exec command without port option uses None for additional_ports."""
        runner = CliRunner()

        # Mock successful execution
        from types import SimpleNamespace

        mock_execute.return_value = SimpleNamespace(returncode=0)

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            result = runner.invoke(
                cli, ["exec", "--workspace", str(workspace), "--", "python", "app.py"]
            )

            assert result.exit_code == 0
            mock_execute.assert_called_once_with(
                workspace=workspace,
                command=["python", "app.py"],
                additional_ports=None,
                auto_up=True,
            )
            mock_exit.assert_any_call(0)

    @patch("sys.exit")
    @patch("devcontainer_tools.container.execute_in_container")
    def test_exec_with_no_up_option(self, mock_execute, mock_exit):
        """Test exec command with --no-up option."""
        runner = CliRunner()

        # Mock successful execution
        from types import SimpleNamespace

        mock_execute.return_value = SimpleNamespace(returncode=0)

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            result = runner.invoke(
                cli, ["exec", "--workspace", str(workspace), "--no-up", "--", "ls", "-la"]
            )

            assert result.exit_code == 0
            mock_execute.assert_called_once_with(
                workspace=workspace, command=["ls", "-la"], additional_ports=None, auto_up=False
            )
            mock_exit.assert_any_call(0)


class TestCliStatus:
    """Test the status command."""

    @patch("devcontainer_tools.container.run_command")
    @patch("devcontainer_tools.utils.find_devcontainer_json")
    def test_status_running_container(self, mock_find_config, mock_run_command):
        """Test status with running container."""
        runner = CliRunner()

        # Mock run_command to simulate container operations
        from types import SimpleNamespace

        def mock_run_command_side_effect(cmd, **kwargs):
            if cmd[0] == "docker" and cmd[1] == "ps":
                # get_container_id の呼び出し
                return SimpleNamespace(returncode=0, stdout="abc123container\n", stderr="")
            elif cmd[0] == "docker" and cmd[1] == "inspect":
                # get_container_info の呼び出し
                container_info = [
                    {
                        "Config": {"Image": "test-image:latest"},
                        "Mounts": [{"Source": "/host/path", "Destination": "/container/path"}],
                    }
                ]
                return SimpleNamespace(returncode=0, stdout=json.dumps(container_info), stderr="")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        mock_run_command.side_effect = mock_run_command_side_effect
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            # Create a mock devcontainer.json
            config_path = workspace / ".devcontainer" / "devcontainer.json"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text('{"name": "test"}')
            mock_find_config.return_value = config_path

            result = runner.invoke(cli, ["status", "--workspace", str(workspace)])

            assert result.exit_code == 0
            assert "Running" in result.output
            assert "abc123container"[:12] in result.output
            assert "test-image:latest" in result.output

    @patch("devcontainer_tools.container.get_container_id")
    @patch("devcontainer_tools.utils.find_devcontainer_json")
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

    @patch("subprocess.run")
    def test_rebuild(self, mock_subprocess):
        """Test rebuild command."""
        runner = CliRunner()

        mock_subprocess.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            # Create devcontainer.json
            devcontainer_path = workspace / ".devcontainer" / "devcontainer.json"
            devcontainer_path.parent.mkdir(parents=True, exist_ok=True)
            devcontainer_path.write_text('{"name": "test"}')

            result = runner.invoke(cli, ["rebuild", "--workspace", str(workspace)])

            assert result.exit_code == 0

            # Verify that clean and no-cache options were used
            args = mock_subprocess.call_args[0][0]
            assert "--remove-existing-container" in args
            assert "--build-no-cache" in args


class TestCliDown:
    """Test the down command."""

    @patch("devcontainer_tools.container.run_command")
    def test_down_with_running_container(self, mock_run_command):
        """Test down command with running container."""
        runner = CliRunner()

        # Mock container exists - need multiple calls for get_container_id
        from types import SimpleNamespace

        def mock_run_command_side_effect(cmd, **kwargs):
            if cmd[0] == "docker" and cmd[1] == "ps":
                return SimpleNamespace(returncode=0, stdout="mock_container_id\n", stderr="")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        mock_run_command.side_effect = mock_run_command_side_effect

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            result = runner.invoke(cli, ["down", "--workspace", str(workspace)])

            assert result.exit_code == 0
            # Verify the right docker commands were called
            assert any(
                "docker" in str(call) and "stop" in str(call)
                for call in mock_run_command.call_args_list
            )
            assert any(
                "docker" in str(call) and "rm" in str(call)
                for call in mock_run_command.call_args_list
            )

    @patch("devcontainer_tools.container.run_command")
    def test_down_with_volumes_option(self, mock_run_command):
        """Test down command with --volumes option."""
        runner = CliRunner()

        # Mock container exists
        from types import SimpleNamespace

        def mock_run_command_side_effect(cmd, **kwargs):
            if cmd[0] == "docker" and cmd[1] == "ps":
                return SimpleNamespace(returncode=0, stdout="mock_container_id\n", stderr="")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        mock_run_command.side_effect = mock_run_command_side_effect

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            result = runner.invoke(cli, ["down", "--workspace", str(workspace), "--volumes"])

            assert result.exit_code == 0
            # Verify the right docker commands were called including -v flag for volumes
            assert any(
                "docker" in str(call) and "stop" in str(call)
                for call in mock_run_command.call_args_list
            )
            assert any(
                "docker" in str(call) and "rm" in str(call) and "-v" in str(call)
                for call in mock_run_command.call_args_list
            )

    @patch("devcontainer_tools.container.run_command")
    def test_down_no_container(self, mock_run_command):
        """Test down command when no container is running."""
        runner = CliRunner()

        # Mock no container found
        from types import SimpleNamespace

        mock_run_command.return_value = SimpleNamespace(returncode=0, stdout="", stderr="")

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            result = runner.invoke(cli, ["down", "--workspace", str(workspace)])

            assert result.exit_code == 0
            assert "実行中のコンテナが見つかりません" in result.output

    @patch("devcontainer_tools.container.run_command")
    @patch("sys.exit")
    def test_down_failure(self, mock_exit, mock_run_command):
        """Test down command when stop/remove fails."""
        runner = CliRunner()

        # Mock container exists but stop/remove fails
        from types import SimpleNamespace

        def mock_run_command_side_effect(cmd, **kwargs):
            if cmd[0] == "docker" and cmd[1] == "ps":
                return SimpleNamespace(returncode=0, stdout="mock_container_id\n", stderr="")
            elif cmd[0] == "docker" and cmd[1] == "stop":
                return SimpleNamespace(returncode=1, stdout="", stderr="Container stop failed")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        mock_run_command.side_effect = mock_run_command_side_effect

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            result = runner.invoke(cli, ["down", "--workspace", str(workspace)])

            assert result.exit_code == 0  # sys.exit is mocked
            # Check that sys.exit(1) was called (may be called multiple times by Click)
            mock_exit.assert_any_call(1)
            assert "コンテナの停止・削除に失敗しました" in result.output


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
        assert "--auto-forward-ports" in result.output

    def test_down_help(self):
        """Test down command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["down", "--help"])
        assert result.exit_code == 0
        assert "開発コンテナを停止" in result.output
