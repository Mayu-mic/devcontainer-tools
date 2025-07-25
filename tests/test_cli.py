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

    def test_up_with_short_port_option(self):
        """Test up command with -p short option for port forwarding."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            # Create devcontainer.json
            devcontainer_path = workspace / ".devcontainer" / "devcontainer.json"
            devcontainer_path.parent.mkdir(parents=True, exist_ok=True)
            devcontainer_path.write_text('{"name": "test", "image": "python:3.12"}')

            # 共通設定ファイルがないことを確認
            common_config_path = Path(temp_dir) / "common.json"

            result = runner.invoke(
                cli,
                [
                    "up",
                    "--workspace",
                    str(workspace),
                    "--dry-run",
                    "-p",
                    "3000",
                    "-p",
                    "5000:5000",
                    "--common-config",
                    str(common_config_path),
                ],
            )

            assert result.exit_code == 0
            # マージ後の設定にappPortが含まれていることを確認
            assert '"appPort"' in result.output
            assert "3000" in result.output
            assert "5000:5000" in result.output

    @patch("subprocess.run")
    def test_up_with_rebuild_flag(self, mock_subprocess):
        """Test up command with --rebuild flag."""
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
                    "--rebuild",
                ],
            )

            assert result.exit_code == 0

            # Verify --rebuild implies --clean and --no-cache
            args = mock_subprocess.call_args[0][0]
            assert "--remove-existing-container" in args
            assert "--build-no-cache" in args

    @patch("subprocess.run")
    def test_up_with_rebuild_and_other_options(self, mock_subprocess):
        """Test up command with --rebuild and other options."""
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
                    "--rebuild",
                    "--port",
                    "3000",
                    "--mount",
                    "/host:/container",
                    "--env",
                    "NODE_ENV=development",
                ],
            )

            assert result.exit_code == 0

            # Verify --rebuild implies --clean and --no-cache
            args = mock_subprocess.call_args[0][0]
            assert "--remove-existing-container" in args
            assert "--build-no-cache" in args

    @patch("subprocess.run")
    def test_up_with_rebuild_and_no_cache_flag(self, mock_subprocess):
        """Test up command with --rebuild and --no-cache flag combination."""
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
                    "--rebuild",
                    "--no-cache",
                ],
            )

            assert result.exit_code == 0

            # Verify --rebuild implies --clean and --no-cache
            args = mock_subprocess.call_args[0][0]
            assert "--remove-existing-container" in args
            assert "--build-no-cache" in args


class TestCliExec:
    """Test the exec command."""

    @patch("sys.exit")
    @patch("subprocess.run")
    def test_exec_command(self, mock_subprocess, mock_exit):
        """Test exec command."""
        runner = CliRunner()

        # Mock successful execution - コンテナチェックとexec実行の両方
        def mock_subprocess_side_effect(cmd, **kwargs):
            if cmd[0] == "docker" and cmd[1] == "ps":
                # get_container_id returns container ID (container is running)
                return MagicMock(returncode=0, stdout="abc123container\n", stderr="")
            elif cmd[0] == "devcontainer" and cmd[1] == "exec":
                return MagicMock(returncode=0)
            return MagicMock(returncode=0)

        mock_subprocess.side_effect = mock_subprocess_side_effect

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            # Create devcontainer.json
            devcontainer_path = workspace / ".devcontainer" / "devcontainer.json"
            devcontainer_path.parent.mkdir(parents=True, exist_ok=True)
            devcontainer_path.write_text('{"name": "test"}')

            result = runner.invoke(
                cli, ["exec", "--workspace", str(workspace), "--", "bash", "-c", "echo hello"]
            )

            # テストアサーション
            assert result.exit_code == 0
            # docker ps でコンテナチェックが行われることを確認
            docker_calls = [
                call
                for call in mock_subprocess.call_args_list
                if len(call[0]) > 0 and call[0][0][0] == "docker"
            ]
            assert len(docker_calls) >= 1
            # devcontainer exec が呼び出されることを確認
            exec_calls = [
                call
                for call in mock_subprocess.call_args_list
                if len(call[0]) > 0 and call[0][0][0] == "devcontainer"
            ]
            assert len(exec_calls) >= 1
            # sys.exit(0)が呼び出されることを確認
            mock_exit.assert_any_call(0)

    @patch("sys.exit")
    @patch("subprocess.run")
    def test_exec_command_failure(self, mock_subprocess, mock_exit):
        """Test exec command when command fails."""
        runner = CliRunner()

        # Mock successful container check but failed exec
        def mock_subprocess_side_effect(cmd, **kwargs):
            if cmd[0] == "docker" and cmd[1] == "ps":
                # コンテナは起動している
                return MagicMock(returncode=0, stdout="abc123container\n", stderr="")
            elif cmd[0] == "devcontainer" and cmd[1] == "exec":
                # exec コマンドは失敗
                return MagicMock(returncode=127)
            return MagicMock(returncode=0)

        mock_subprocess.side_effect = mock_subprocess_side_effect

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            # Create devcontainer.json
            devcontainer_path = workspace / ".devcontainer" / "devcontainer.json"
            devcontainer_path.parent.mkdir(parents=True, exist_ok=True)
            devcontainer_path.write_text('{"name": "test"}')

            result = runner.invoke(
                cli, ["exec", "--workspace", str(workspace), "nonexistent-command"]
            )

            # テストアサーション
            assert result.exit_code == 0  # sys.exit() is mocked, so CliRunner sees success
            # devcontainer exec が呼び出されることを確認
            exec_calls = [
                call
                for call in mock_subprocess.call_args_list
                if len(call[0]) > 0 and call[0][0][0] == "devcontainer"
            ]
            assert len(exec_calls) >= 1
            # sys.exit(127)が呼び出されることを確認
            mock_exit.assert_any_call(127)

    @patch("sys.exit")
    @patch("subprocess.run")
    def test_exec_without_workspace_option_uses_default(self, mock_subprocess, mock_exit):
        """
        Test exec command without --workspace option uses default workspace folder

        期待される動作:
        - --workspaceオプションなしの場合、workspace=Noneが渡される
        - 現在のディレクトリでコンテナチェックが実行される
        - execute_in_containerでworkspace_folder="."が使用される
        """
        runner = CliRunner()

        # Mock successful execution - コンテナチェックも含む
        def mock_subprocess_side_effect(cmd, **kwargs):
            if cmd[0] == "docker" and cmd[1] == "ps":
                # コンテナは起動している（現在のディレクトリ）
                return MagicMock(returncode=0, stdout="abc123container\n", stderr="")
            elif cmd[0] == "devcontainer" and cmd[1] == "exec":
                return MagicMock(returncode=0)
            return MagicMock(returncode=0)

        mock_subprocess.side_effect = mock_subprocess_side_effect

        result = runner.invoke(cli, ["exec", "pwd"])

        # テストアサーション
        assert result.exit_code == 0
        # docker ps でコンテナチェックが行われることを確認
        docker_calls = [
            call
            for call in mock_subprocess.call_args_list
            if len(call[0]) > 0 and call[0][0][0] == "docker"
        ]
        assert len(docker_calls) >= 1
        # devcontainer exec が呼び出されることを確認
        exec_calls = [
            call
            for call in mock_subprocess.call_args_list
            if len(call[0]) > 0 and call[0][0][0] == "devcontainer"
        ]
        assert len(exec_calls) >= 1
        mock_exit.assert_any_call(0)

    @patch("sys.exit")
    @patch("subprocess.run")
    def test_exec_without_port_option(self, mock_subprocess, mock_exit):
        """Test exec command without -p port option."""
        runner = CliRunner()

        # Mock successful execution - コンテナチェックも含む
        def mock_subprocess_side_effect(cmd, **kwargs):
            if cmd[0] == "docker" and cmd[1] == "ps":
                # コンテナは起動している
                return MagicMock(returncode=0, stdout="abc123container\n", stderr="")
            elif cmd[0] == "devcontainer" and cmd[1] == "exec":
                return MagicMock(returncode=0)
            return MagicMock(returncode=0)

        mock_subprocess.side_effect = mock_subprocess_side_effect

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            # Create devcontainer.json
            devcontainer_path = workspace / ".devcontainer" / "devcontainer.json"
            devcontainer_path.parent.mkdir(parents=True, exist_ok=True)
            devcontainer_path.write_text('{"name": "test"}')

            result = runner.invoke(
                cli, ["exec", "--workspace", str(workspace), "--", "python", "app.py"]
            )

            # テストアサーション
            assert result.exit_code == 0
            # devcontainer exec が呼び出されることを確認
            exec_calls = [
                call
                for call in mock_subprocess.call_args_list
                if len(call[0]) > 0 and call[0][0][0] == "devcontainer"
            ]
            assert len(exec_calls) >= 1

            # devcontainer execの引数を確認
            exec_call_args = exec_calls[0][0][0]
            assert exec_call_args[0] == "devcontainer"
            assert exec_call_args[1] == "exec"
            assert exec_call_args[2] == "--workspace-folder"
            assert exec_call_args[3] == "."
            assert exec_call_args[4] == "python"
            assert exec_call_args[5] == "app.py"
            # sys.exit(0)が呼び出されることを確認
            mock_exit.assert_any_call(0)

    @patch("sys.exit")
    @patch("subprocess.run")
    def test_exec_container_not_running_shows_error(self, mock_subprocess, mock_exit):
        """Test exec command when container is not running - should show clear error message."""
        runner = CliRunner()

        # Mock container not found (empty stdout) - コンテナチェックのために docker ps を呼び出す
        def mock_subprocess_side_effect(cmd, **kwargs):
            if cmd[0] == "docker" and cmd[1] == "ps":
                # get_container_id returns None (no container found)
                return MagicMock(returncode=0, stdout="", stderr="")
            return MagicMock(returncode=0)

        mock_subprocess.side_effect = mock_subprocess_side_effect

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            # Create devcontainer.json
            devcontainer_path = workspace / ".devcontainer" / "devcontainer.json"
            devcontainer_path.parent.mkdir(parents=True, exist_ok=True)
            devcontainer_path.write_text('{"name": "test"}')

            result = runner.invoke(cli, ["exec", "--workspace", str(workspace), "--", "ls", "-la"])

            # テストアサーション: コンテナが起動していない場合、事前チェックでエラーになる
            assert result.exit_code == 0  # sys.exit is mocked
            # 適切なエラーメッセージが表示されることを確認
            assert "コンテナが起動していません" in result.output
            assert "先に 'dev up' を実行してください" in result.output
            # sys.exit(1)が呼び出されることを確認（コンテナ未起動エラー）
            mock_exit.assert_any_call(1)


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
    def test_rebuild_shows_deprecation_warning(self, mock_subprocess):
        """Test rebuild command shows deprecation warning."""
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

            # Verify deprecation warning is shown
            assert "deprecate" in result.output.lower() or "非推奨" in result.output

            # Verify that clean and no-cache options were used
            args = mock_subprocess.call_args[0][0]
            assert "--remove-existing-container" in args
            assert "--build-no-cache" in args

    @patch("subprocess.run")
    def test_rebuild_with_additional_options(self, mock_subprocess):
        """Test rebuild command passes additional options through."""
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
                    "rebuild",
                    "--workspace",
                    str(workspace),
                    "--port",
                    "3000",
                    "--mount",
                    "/host:/container",
                    "--env",
                    "NODE_ENV=development",
                ],
            )

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
    def test_down_with_docker_compose(self, mock_run_command):
        """Test down command with docker-compose project."""
        runner = CliRunner()

        # Mock docker-compose scenario
        from types import SimpleNamespace

        def mock_run_command_side_effect(cmd, **kwargs):
            if cmd[0] == "docker" and cmd[1] == "ps":
                # 単一コンテナの場合
                return SimpleNamespace(returncode=0, stdout="mock_container_id\n", stderr="")
            elif cmd[0] == "docker" and "compose" in cmd:
                # docker-composeコマンドの場合
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        mock_run_command.side_effect = mock_run_command_side_effect

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            # Create docker-compose.yml
            docker_compose_file = workspace / "docker-compose.yml"
            docker_compose_file.write_text(
                "version: '3.8'\nservices:\n  app:\n    build: .\n    ports:\n      - 3000:3000"
            )
            # Create devcontainer.json with dockerComposeFile
            devcontainer_path = workspace / ".devcontainer" / "devcontainer.json"
            devcontainer_path.parent.mkdir(parents=True, exist_ok=True)
            devcontainer_path.write_text(
                '{"name": "test", "dockerComposeFile": "../docker-compose.yml", "service": "app"}'
            )

            result = runner.invoke(cli, ["down", "--workspace", str(workspace)])

            assert result.exit_code == 0
            # docker-composeを使用する場合は、compose用のコマンドが呼ばれることを確認
            compose_calls = [
                call for call in mock_run_command.call_args_list if "compose" in str(call)
            ]
            # 修正後は compose down コマンドが呼ばれる
            assert len(compose_calls) > 0
            # -f オプションでファイルが指定されることを確認
            compose_down_calls = [
                call
                for call in mock_run_command.call_args_list
                if "compose" in str(call) and "down" in str(call)
            ]
            assert len(compose_down_calls) > 0

    @patch("devcontainer_tools.container.run_command")
    def test_down_compose_multiple_containers(self, mock_run_command):
        """Test down command with multiple containers from docker-compose."""
        runner = CliRunner()

        # Mock multiple containers scenario
        from types import SimpleNamespace

        def mock_run_command_side_effect(cmd, **kwargs):
            if cmd[0] == "docker" and cmd[1] == "ps":
                # 複数コンテナのシナリオ
                return SimpleNamespace(
                    returncode=0, stdout="container1\ncontainer2\ncontainer3\n", stderr=""
                )
            elif cmd[0] == "docker" and "compose" in cmd:
                # docker-composeコマンドの場合
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        mock_run_command.side_effect = mock_run_command_side_effect

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            # Create docker-compose.yml with multiple services
            docker_compose_file = workspace / "docker-compose.yml"
            docker_compose_file.write_text(
                "version: '3.8'\nservices:\n  app:\n    build: .\n  db:\n    image: postgres\n  redis:\n    image: redis"
            )
            # Create devcontainer.json with dockerComposeFile
            devcontainer_path = workspace / ".devcontainer" / "devcontainer.json"
            devcontainer_path.parent.mkdir(parents=True, exist_ok=True)
            devcontainer_path.write_text(
                '{"name": "test", "dockerComposeFile": "../docker-compose.yml", "service": "app"}'
            )

            result = runner.invoke(cli, ["down", "--workspace", str(workspace)])

            assert result.exit_code == 0
            # 修正後は compose down コマンドが使用される
            compose_calls = [
                call for call in mock_run_command.call_args_list if "compose" in str(call)
            ]
            assert len(compose_calls) > 0
            # 複数コンテナの場合でも compose down が呼ばれる
            compose_down_calls = [
                call
                for call in mock_run_command.call_args_list
                if "compose" in str(call) and "down" in str(call)
            ]
            assert len(compose_down_calls) > 0

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
        assert "--rebuild" in result.output

    def test_down_help(self):
        """Test down command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["down", "--help"])
        assert result.exit_code == 0
        assert "開発コンテナを停止" in result.output
