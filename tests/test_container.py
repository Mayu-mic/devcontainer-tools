"""
コンテナ操作のテスト
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from devcontainer_tools.container import (
    ensure_container_running,
    execute_in_container,
    run_command,
)


class TestExecuteInContainer:
    """execute_in_container関数のテスト"""

    @patch("subprocess.run")
    def test_devcontainer_exec_without_ports(self, mock_run):
        """ポート指定なしでdevcontainer execを使用"""
        # Arrange
        workspace = Path("/test/workspace")
        command = ["pwd"]
        mock_run.return_value = MagicMock(returncode=0)

        # Act
        result = execute_in_container(
            workspace=workspace,
            command=command,
        )

        # Assert
        mock_run.assert_called_once_with(
            ["devcontainer", "exec", "--workspace-folder", ".", "pwd"],
            text=True,
        )
        assert result.returncode == 0

    @patch("subprocess.run")
    def test_no_auto_up_functionality(self, mock_run):
        """auto_up機能が削除されていることを確認"""
        # Arrange
        workspace = Path("/test/workspace")
        command = ["echo", "test"]
        mock_run.return_value = MagicMock(returncode=0)

        # Act
        result = execute_in_container(
            workspace=workspace,
            command=command,
        )

        # Assert
        # ensure_container_runningは呼び出されない（自動起動機能が削除されたため）
        mock_run.assert_called_once_with(
            ["devcontainer", "exec", "--workspace-folder", ".", "echo", "test"],
            text=True,
        )
        assert result.returncode == 0

    @patch("devcontainer_tools.container.is_container_running")
    @patch("subprocess.run")
    def test_container_not_running_error_message(self, mock_run, mock_is_running):
        """コンテナが起動していない場合のエラーメッセージを確認"""
        # Arrange
        workspace = Path("/test/workspace")
        command = ["echo", "test"]
        mock_is_running.return_value = False

        # execute_in_containerの実装が変更されるため、適切な動作を確認
        mock_run.return_value = MagicMock(returncode=1, stderr="Container not running")

        # Act
        result = execute_in_container(
            workspace=workspace,
            command=command,
        )

        # Assert
        # コンテナが起動していない場合でもdevcontainer execは実行される
        # （実際のエラーハンドリングはCLI層で行われる）
        mock_run.assert_called_once_with(
            ["devcontainer", "exec", "--workspace-folder", ".", "echo", "test"],
            text=True,
        )
        assert result.returncode == 1

    @patch("subprocess.run")
    def test_devcontainer_exec_without_auto_up(self, mock_run):
        """自動起動機能が削除されていることを確認"""
        # Arrange
        workspace = Path("/test/workspace")
        command = ["ls", "-la"]
        mock_run.return_value = MagicMock(returncode=0)
        # Act
        result = execute_in_container(
            workspace=workspace,
            command=command,
        )

        # Assert
        mock_run.assert_called_once_with(
            ["devcontainer", "exec", "--workspace-folder", ".", "ls", "-la"],
            text=True,
        )
        assert result.returncode == 0


class TestRunCommand:
    """run_command関数のテスト"""

    @patch("subprocess.run")
    def test_run_command_basic(self, mock_subprocess_run):
        """基本的なコマンド実行のテスト"""
        # Arrange
        cmd = ["echo", "test"]
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "test\n"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        # Act
        result = run_command(cmd)

        # Assert
        mock_subprocess_run.assert_called_once_with(cmd, check=True, capture_output=True, text=True)
        assert result.returncode == 0

    @patch("subprocess.run")
    def test_run_command_with_verbose(self, mock_subprocess_run):
        """verboseオプション付きのコマンド実行テスト"""
        # Arrange
        cmd = ["echo", "test"]
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "test output"
        mock_result.stderr = "some stderr"
        mock_subprocess_run.return_value = mock_result

        # Act
        result = run_command(cmd, verbose=True)

        # Assert
        mock_subprocess_run.assert_called_once_with(cmd, check=True, capture_output=True, text=True)
        assert result.returncode == 0

    @patch("subprocess.run")
    def test_run_command_with_error(self, mock_subprocess_run):
        """エラー時のコマンド実行テスト"""
        # Arrange
        cmd = ["false"]
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "command failed"
        mock_subprocess_run.return_value = mock_result

        # Act
        result = run_command(cmd, check=False, verbose=True)

        # Assert
        mock_subprocess_run.assert_called_once_with(
            cmd, check=False, capture_output=True, text=True
        )
        assert result.returncode == 1


class TestEnsureContainerRunning:
    """ensure_container_running関数のテスト"""

    @patch("devcontainer_tools.container.is_container_running")
    def test_container_already_running(self, mock_is_running):
        """コンテナが既に起動している場合のテスト"""
        # Arrange
        workspace = Path("/test/workspace")
        mock_is_running.return_value = True

        # Act
        result = ensure_container_running(workspace)

        # Assert
        assert result is True
        mock_is_running.assert_called_once_with(workspace)

    @patch("devcontainer_tools.container.run_command")
    @patch("devcontainer_tools.container.is_container_running")
    def test_container_start_success(self, mock_is_running, mock_run_command):
        """コンテナの起動が成功する場合のテスト"""
        # Arrange
        workspace = Path("/test/workspace")
        mock_is_running.return_value = False
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run_command.return_value = mock_result

        # Act
        result = ensure_container_running(workspace)

        # Assert
        assert result is True
        mock_run_command.assert_called_once_with(
            ["devcontainer", "up", "--workspace-folder", str(workspace)], check=False, verbose=True
        )

    @patch("devcontainer_tools.container.run_command")
    @patch("devcontainer_tools.container.is_container_running")
    def test_container_start_failure_with_stderr(self, mock_is_running, mock_run_command):
        """コンテナの起動が失敗する場合のテスト（stderrあり）"""
        # Arrange
        workspace = Path("/test/workspace")
        mock_is_running.return_value = False
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Docker daemon not running"
        mock_result.stdout = ""
        mock_run_command.return_value = mock_result

        # Act
        result = ensure_container_running(workspace)

        # Assert
        assert result is False

    @patch("devcontainer_tools.container.run_command")
    @patch("devcontainer_tools.container.is_container_running")
    def test_container_start_failure_with_stdout_only(self, mock_is_running, mock_run_command):
        """コンテナの起動が失敗する場合のテスト（stdoutのみ）"""
        # Arrange
        workspace = Path("/test/workspace")
        mock_is_running.return_value = False
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = ""
        mock_result.stdout = "Error in stdout"
        mock_run_command.return_value = mock_result

        # Act
        result = ensure_container_running(workspace)

        # Assert
        assert result is False

    @patch("devcontainer_tools.container.run_command")
    @patch("devcontainer_tools.container.is_container_running")
    def test_container_start_failure_no_output(self, mock_is_running, mock_run_command):
        """コンテナの起動が失敗する場合のテスト（出力なし）"""
        # Arrange
        workspace = Path("/test/workspace")
        mock_is_running.return_value = False
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = ""
        mock_result.stdout = ""
        mock_run_command.return_value = mock_result

        # Act
        result = ensure_container_running(workspace)

        # Assert
        assert result is False

    @patch("devcontainer_tools.container.run_command")
    @patch("devcontainer_tools.container.is_container_running")
    def test_container_start_exception(self, mock_is_running, mock_run_command):
        """コンテナの起動中に例外が発生する場合のテスト"""
        # Arrange
        workspace = Path("/test/workspace")
        mock_is_running.return_value = False
        mock_run_command.side_effect = Exception("Unexpected error")

        # Act
        result = ensure_container_running(workspace)

        # Assert
        assert result is False
