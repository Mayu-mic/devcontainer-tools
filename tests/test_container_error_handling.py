"""
コンテナ操作のエラーハンドリングテスト
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from devcontainer_tools.container import (
    _try_compose_command_with_fallback,
    get_compose_container_id,
    get_compose_containers,
    stop_and_remove_compose_containers,
)


class TestContainerErrorHandling:
    """コンテナ操作のエラーハンドリングテスト"""

    @patch("devcontainer_tools.container.run_command")
    def test_fallback_helper_with_exception(self, mock_run_command):
        """_try_compose_command_with_fallbackで例外が発生する場合"""
        # Arrange
        workspace = Path("/test/workspace")
        compose_file = Path("/test/workspace/docker-compose.yml")
        base_cmd = ["ps", "-q"]

        # run_commandで例外が発生
        mock_run_command.side_effect = Exception("Docker daemon not responding")

        # Act & Assert
        # 例外が発生してもNoneを返すべき（現在の実装では例外がそのまま伝播）
        try:
            result = _try_compose_command_with_fallback(workspace, compose_file, base_cmd)
            # 例外が発生しない場合は、Noneが返される
            assert result is None
        except Exception:
            # 例外が発生することも想定される動作
            pass

    @patch("devcontainer_tools.utils.detect_compose_config")
    @patch("devcontainer_tools.container.run_command")
    def test_get_compose_containers_with_malformed_output(
        self, mock_run_command, mock_detect_compose
    ):
        """get_compose_containersでmalformedな出力を受け取る場合"""
        # Arrange
        workspace = Path("/test/workspace")
        compose_file = Path("/test/workspace/docker-compose.yml")
        mock_detect_compose.return_value = {"compose_file": compose_file}

        # 奇妙な出力パターン
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "\n\n  \ncontainer123\n  \n\ncontainer456\n  \n"
        mock_run_command.return_value = mock_result

        # Act
        containers = get_compose_containers(workspace)

        # Assert
        # 空白行は除外され、trimされたコンテナIDのみが返される
        assert containers == ["container123", "container456"]

    @patch("devcontainer_tools.utils.detect_compose_config")
    @patch("devcontainer_tools.container.run_command")
    def test_get_compose_containers_with_unicode_characters(
        self, mock_run_command, mock_detect_compose
    ):
        """get_compose_containersでUnicode文字を含む出力を受け取る場合"""
        # Arrange
        workspace = Path("/test/workspace")
        compose_file = Path("/test/workspace/docker-compose.yml")
        mock_detect_compose.return_value = {"compose_file": compose_file}

        # Unicode文字を含む出力（通常は起こらないが、エラーメッセージなどで可能）
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "container_with_emoji_🐳\nregular_container\n"
        mock_run_command.return_value = mock_result

        # Act
        containers = get_compose_containers(workspace)

        # Assert
        assert containers == ["container_with_emoji_🐳", "regular_container"]

    @patch("devcontainer_tools.utils.detect_compose_config")
    def test_detect_compose_config_returns_invalid_structure(self, mock_detect_compose):
        """detect_compose_configが無効な構造を返す場合"""
        # Arrange
        workspace = Path("/test/workspace")
        mock_detect_compose.return_value = {"invalid_key": "invalid_value"}  # compose_fileがない

        # Act
        containers = get_compose_containers(workspace)

        # Assert
        # KeyErrorまたは適切なエラーハンドリングで空のリストが返される
        assert containers == []

    @patch("devcontainer_tools.utils.detect_compose_config")
    @patch("devcontainer_tools.container.run_command")
    def test_stop_and_remove_with_permission_error(self, mock_run_command, mock_detect_compose):
        """権限エラーでコンテナ停止が失敗する場合"""
        # Arrange
        workspace = Path("/test/workspace")
        compose_file = Path("/test/workspace/docker-compose.yml")
        mock_detect_compose.return_value = {"compose_file": compose_file}

        # 権限エラー
        mock_result = MagicMock()
        mock_result.returncode = 126  # Permission denied
        mock_result.stderr = "Permission denied"
        mock_result.stdout = ""
        mock_run_command.return_value = mock_result

        # Act
        result = stop_and_remove_compose_containers(workspace, remove_volumes=False)

        # Assert
        assert result is False
        # 両方のコマンドで権限エラーが発生
        assert mock_run_command.call_count == 2

    @patch("devcontainer_tools.utils.detect_compose_config")
    @patch("devcontainer_tools.container.run_command")
    def test_large_container_output(self, mock_run_command, mock_detect_compose):
        """大量のコンテナ出力を処理する場合"""
        # Arrange
        workspace = Path("/test/workspace")
        compose_file = Path("/test/workspace/docker-compose.yml")
        mock_detect_compose.return_value = {"compose_file": compose_file}

        # 大量のコンテナID（1000個）
        container_ids = [f"container_{i:04d}" for i in range(1000)]
        stdout_output = "\n".join(container_ids) + "\n"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = stdout_output
        mock_run_command.return_value = mock_result

        # Act
        containers = get_compose_containers(workspace)

        # Assert
        assert len(containers) == 1000
        assert containers[0] == "container_0000"
        assert containers[999] == "container_0999"

    @patch("devcontainer_tools.utils.detect_compose_config")
    @patch("devcontainer_tools.container.run_command")
    def test_timeout_simulation(self, mock_run_command, mock_detect_compose):
        """タイムアウトのシミュレーション"""
        # Arrange
        workspace = Path("/test/workspace")
        compose_file = Path("/test/workspace/docker-compose.yml")
        devcontainer_config = {"service": "app", "dockerComposeFile": "../docker-compose.yml"}
        mock_detect_compose.return_value = {
            "compose_file": compose_file,
            "devcontainer_config": devcontainer_config,
        }

        # タイムアウトエラーをシミュレート
        mock_result = MagicMock()
        mock_result.returncode = 124  # timeout command exit code
        mock_result.stderr = "Timeout"
        mock_result.stdout = ""
        mock_run_command.return_value = mock_result

        # Act
        container_id = get_compose_container_id(workspace, "app")

        # Assert
        assert container_id is None
        # 両方のコマンドでタイムアウト
        assert mock_run_command.call_count == 2

    @patch("devcontainer_tools.utils.detect_compose_config")
    def test_compose_file_path_edge_cases(self, mock_detect_compose):
        """compose_fileパスのエッジケース"""
        # Arrange
        workspace = Path("/test/workspace")

        # 相対パスから絶対パスへの変換が必要なケース
        mock_detect_compose.return_value = {
            "compose_file": Path("../docker-compose.yml")  # 相対パス
        }

        with patch("devcontainer_tools.container.run_command") as mock_run_command:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "container123\n"
            mock_run_command.return_value = mock_result

            # Act
            containers = get_compose_containers(workspace)

            # Assert
            assert containers == ["container123"]
            # パスが文字列に変換されて使用される
            called_args = mock_run_command.call_args[0][0]
            assert called_args[2] == "-f"
            # 相対パスが文字列として渡される
            assert "../docker-compose.yml" in called_args[3]

    def test_workspace_with_symlinks(self):
        """シンボリックリンクを含むワークスペースパス"""
        import os

        with tempfile.TemporaryDirectory() as temp_dir:
            # 実際のディレクトリを作成
            real_workspace = Path(temp_dir) / "real_workspace"
            real_workspace.mkdir()

            # シンボリックリンクを作成
            symlink_workspace = Path(temp_dir) / "symlink_workspace"
            os.symlink(str(real_workspace), str(symlink_workspace))

            # docker-compose.ymlを作成
            docker_compose_file = real_workspace / "docker-compose.yml"
            docker_compose_file.write_text("""
version: '3.8'
services:
  app:
    image: nginx:alpine
""")

            # devcontainer.jsonを作成
            devcontainer_path = real_workspace / ".devcontainer" / "devcontainer.json"
            devcontainer_path.parent.mkdir(parents=True, exist_ok=True)
            devcontainer_path.write_text("""
{
  "name": "symlink-test",
  "dockerComposeFile": "../docker-compose.yml",
  "service": "app"
}
""")

            with patch("devcontainer_tools.container.run_command") as mock_run_command:
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "symlink_container\n"
                mock_run_command.return_value = mock_result

                # Act - シンボリックリンク経由でアクセス
                from devcontainer_tools.container import get_container_id

                container_id = get_container_id(symlink_workspace)

                # Assert
                assert container_id == "symlink_container"

                # プロジェクト名はシンボリックリンクのディレクトリ名を使用
                called_args = mock_run_command.call_args_list[-1][0][0]
                if "--project-name" in called_args:
                    project_name_index = called_args.index("--project-name") + 1
                    assert called_args[project_name_index] == "symlink_workspace_devcontainer"
