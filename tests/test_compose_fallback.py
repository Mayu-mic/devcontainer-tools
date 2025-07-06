"""
_try_compose_command_with_fallback関数のテスト
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from devcontainer_tools.container import _try_compose_command_with_fallback


class TestTryComposeCommandWithFallback:
    """_try_compose_command_with_fallback関数のテスト"""

    @patch("devcontainer_tools.container.run_command")
    def test_first_command_succeeds(self, mock_run_command):
        """最初のコマンドが成功する場合"""
        # Arrange
        workspace = Path("/test/workspace")
        compose_file = Path("/test/workspace/docker-compose.yml")
        base_cmd = ["ps", "-q"]

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "container123\n"
        mock_run_command.return_value = mock_result

        # Act
        result = _try_compose_command_with_fallback(workspace, compose_file, base_cmd)

        # Assert
        assert result is not None
        assert result.stdout == "container123\n"
        # 1回だけ呼び出される（最初のコマンドで成功）
        mock_run_command.assert_called_once_with(
            ["docker", "compose", "-f", str(compose_file), "ps", "-q"], check=False
        )

    @patch("devcontainer_tools.container.run_command")
    def test_fallback_to_devcontainer_project_name(self, mock_run_command):
        """フォールバックでdevcontainerプロジェクト名を使用する場合"""
        # Arrange
        workspace = Path("/test/workspace")
        compose_file = Path("/test/workspace/docker-compose.yml")
        base_cmd = ["ps", "-q", "app"]

        # 最初のコマンドは失敗、2番目のコマンドは成功
        mock_results = [
            MagicMock(returncode=0, stdout=""),  # 空の結果
            MagicMock(returncode=0, stdout="container456\n"),  # 成功
        ]
        mock_run_command.side_effect = mock_results

        # Act
        result = _try_compose_command_with_fallback(workspace, compose_file, base_cmd)

        # Assert
        assert result is not None
        assert result.stdout == "container456\n"
        # 2回呼び出される
        assert mock_run_command.call_count == 2

        # 1回目のコール
        first_call = mock_run_command.call_args_list[0]
        assert first_call[0][0] == ["docker", "compose", "-f", str(compose_file), "ps", "-q", "app"]

        # 2回目のコール（devcontainerプロジェクト名付き）
        second_call = mock_run_command.call_args_list[1]
        expected_project_name = f"{workspace.name}_devcontainer"
        assert second_call[0][0] == [
            "docker",
            "compose",
            "--project-name",
            expected_project_name,
            "-f",
            str(compose_file),
            "ps",
            "-q",
            "app",
        ]

    @patch("devcontainer_tools.container.run_command")
    def test_both_commands_fail(self, mock_run_command):
        """両方のコマンドが失敗する場合"""
        # Arrange
        workspace = Path("/test/workspace")
        compose_file = Path("/test/workspace/docker-compose.yml")
        base_cmd = ["ps", "-q"]

        # 両方のコマンドが失敗
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_run_command.return_value = mock_result

        # Act
        result = _try_compose_command_with_fallback(workspace, compose_file, base_cmd)

        # Assert
        assert result is None
        # 2回呼び出される
        assert mock_run_command.call_count == 2

    @patch("devcontainer_tools.container.run_command")
    def test_first_command_returns_empty_stdout(self, mock_run_command):
        """最初のコマンドが空のstdoutを返す場合"""
        # Arrange
        workspace = Path("/test/workspace")
        compose_file = Path("/test/workspace/docker-compose.yml")
        base_cmd = ["ps", "-q"]

        # 最初のコマンドは成功だが空、2番目のコマンドは成功
        mock_results = [
            MagicMock(returncode=0, stdout="   \n"),  # 空白のみ
            MagicMock(returncode=0, stdout="container789\n"),  # 成功
        ]
        mock_run_command.side_effect = mock_results

        # Act
        result = _try_compose_command_with_fallback(workspace, compose_file, base_cmd)

        # Assert
        assert result is not None
        assert result.stdout == "container789\n"
        # 2回呼び出される
        assert mock_run_command.call_count == 2

    @patch("devcontainer_tools.container.run_command")
    def test_first_command_non_zero_returncode(self, mock_run_command):
        """最初のコマンドが非ゼロの終了コードを返す場合"""
        # Arrange
        workspace = Path("/test/workspace")
        compose_file = Path("/test/workspace/docker-compose.yml")
        base_cmd = ["ps", "-q"]

        # 最初のコマンドは失敗、2番目のコマンドは成功
        mock_results = [
            MagicMock(returncode=1, stdout="error"),  # 失敗
            MagicMock(returncode=0, stdout="container999\n"),  # 成功
        ]
        mock_run_command.side_effect = mock_results

        # Act
        result = _try_compose_command_with_fallback(workspace, compose_file, base_cmd)

        # Assert
        assert result is not None
        assert result.stdout == "container999\n"
        # 2回呼び出される
        assert mock_run_command.call_count == 2
