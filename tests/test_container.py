"""
コンテナ操作のテスト
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from devcontainer_tools.container import execute_in_container


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
