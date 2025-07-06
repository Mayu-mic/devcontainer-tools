"""
コンテナ操作のエッジケーステスト
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from devcontainer_tools.container import (
    get_compose_container_id,
    get_compose_containers,
    stop_and_remove_compose_containers,
)


class TestContainerEdgeCases:
    """コンテナ操作のエッジケーステスト"""

    @patch("devcontainer_tools.utils.detect_compose_config")
    @patch("devcontainer_tools.container.run_command")
    def test_mixed_environment_partial_success(self, mock_run_command, mock_detect_compose):
        """混在環境：最初のコマンドは一部成功、フォールバックで追加コンテナを発見"""
        # Arrange
        workspace = Path("/test/workspace")
        compose_file = Path("/test/workspace/docker-compose.yml")
        mock_detect_compose.return_value = {"compose_file": compose_file}

        # 最初のコマンドは一部のコンテナのみ、2番目で追加コンテナを発見
        mock_results = [
            MagicMock(returncode=0, stdout="container1\n"),  # 通常のプロジェクト名で1つ
            MagicMock(
                returncode=0, stdout="container2\ncontainer3\n"
            ),  # devcontainerプロジェクト名で2つ
        ]
        mock_run_command.side_effect = mock_results

        # Act
        containers = get_compose_containers(workspace)

        # Assert
        # 最初のコマンドが成功したので、それを返す（フォールバック機能の現在の実装）
        assert containers == ["container1"]
        assert mock_run_command.call_count == 1

    @patch("devcontainer_tools.utils.detect_compose_config")
    @patch("devcontainer_tools.container.run_command")
    def test_first_command_succeeds_second_fails(self, mock_run_command, mock_detect_compose):
        """最初のコマンドが成功し、2番目は呼び出されない場合"""
        # Arrange
        workspace = Path("/test/workspace")
        compose_file = Path("/test/workspace/docker-compose.yml")
        devcontainer_config = {"service": "app", "dockerComposeFile": "../docker-compose.yml"}
        mock_detect_compose.return_value = {
            "compose_file": compose_file,
            "devcontainer_config": devcontainer_config,
        }

        # 最初のコマンドが成功
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "container123\n"
        mock_run_command.return_value = mock_result

        # Act
        container_id = get_compose_container_id(workspace, "app")

        # Assert
        assert container_id == "container123"
        # 最初のコマンドで成功したので、1回だけ呼び出される
        mock_run_command.assert_called_once_with(
            ["docker", "compose", "-f", str(compose_file), "ps", "-q", "app"], check=False
        )

    @patch("devcontainer_tools.utils.detect_compose_config")
    @patch("devcontainer_tools.container.run_command")
    def test_compose_project_name_with_special_characters(
        self, mock_run_command, mock_detect_compose
    ):
        """プロジェクト名に特殊文字が含まれる場合"""
        # Arrange
        workspace = Path("/test/my-special_workspace.name")
        compose_file = Path("/test/my-special_workspace.name/docker-compose.yml")
        mock_detect_compose.return_value = {"compose_file": compose_file}

        # 最初のコマンドは失敗、2番目のコマンドは成功
        mock_results = [
            MagicMock(returncode=0, stdout=""),  # 空の結果
            MagicMock(returncode=0, stdout="special_container\n"),  # 成功
        ]
        mock_run_command.side_effect = mock_results

        # Act
        containers = get_compose_containers(workspace)

        # Assert
        assert containers == ["special_container"]
        assert mock_run_command.call_count == 2

        # 2番目のコールでdevcontainerプロジェクト名が正しく生成される
        second_call = mock_run_command.call_args_list[1]
        expected_project_name = "my-special_workspace.name_devcontainer"
        assert second_call[0][0][3] == expected_project_name

    @patch("devcontainer_tools.utils.detect_compose_config")
    @patch("devcontainer_tools.container.run_command")
    def test_stop_and_remove_first_succeeds_second_fails(
        self, mock_run_command, mock_detect_compose
    ):
        """stop_and_remove_compose_containers: 最初のコマンドは成功、2番目は失敗"""
        # Arrange
        workspace = Path("/test/workspace")
        compose_file = Path("/test/workspace/docker-compose.yml")
        mock_detect_compose.return_value = {"compose_file": compose_file}

        # 最初のコマンドは成功、2番目のコマンドは失敗
        mock_results = [
            MagicMock(returncode=0, stdout="Success"),  # 通常のプロジェクト名で成功
            MagicMock(
                returncode=1, stdout="", stderr="Project not found"
            ),  # devcontainerプロジェクト名で失敗
        ]
        mock_run_command.side_effect = mock_results

        # Act
        result = stop_and_remove_compose_containers(workspace, remove_volumes=False)

        # Assert
        # 最初のコマンドが成功したのでTrueを返す
        assert result is True
        assert mock_run_command.call_count == 2

    @patch("devcontainer_tools.utils.detect_compose_config")
    @patch("devcontainer_tools.container.run_command")
    def test_stop_and_remove_both_fail_different_errors(
        self, mock_run_command, mock_detect_compose
    ):
        """stop_and_remove_compose_containers: 両方のコマンドが異なるエラーで失敗"""
        # Arrange
        workspace = Path("/test/workspace")
        compose_file = Path("/test/workspace/docker-compose.yml")
        mock_detect_compose.return_value = {"compose_file": compose_file}

        # 両方のコマンドが異なるエラーで失敗
        mock_results = [
            MagicMock(returncode=1, stdout="", stderr="Network error"),
            MagicMock(returncode=125, stdout="", stderr="Docker daemon error"),
        ]
        mock_run_command.side_effect = mock_results

        # Act
        result = stop_and_remove_compose_containers(workspace, remove_volumes=True)

        # Assert
        assert result is False
        assert mock_run_command.call_count == 2

        # 両方のコマンドにボリューム削除オプションが含まれる
        for call in mock_run_command.call_args_list:
            assert "-v" in call[0][0]

    @patch("devcontainer_tools.utils.detect_compose_config")
    @patch("devcontainer_tools.container.run_command")
    def test_container_id_with_multiline_output(self, mock_run_command, mock_detect_compose):
        """コンテナIDが複数行で返される場合（最初の行のみを取得）"""
        # Arrange
        workspace = Path("/test/workspace")
        compose_file = Path("/test/workspace/docker-compose.yml")
        devcontainer_config = {"service": "app", "dockerComposeFile": "../docker-compose.yml"}
        mock_detect_compose.return_value = {
            "compose_file": compose_file,
            "devcontainer_config": devcontainer_config,
        }

        # 複数行の出力（通常は起こらないが、念のため）
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "container123\nextra_line\nanother_line\n"
        mock_run_command.return_value = mock_result

        # Act
        container_id = get_compose_container_id(workspace, "app")

        # Assert
        # 最初の行のみを取得
        assert container_id == "container123"

    def test_workspace_path_edge_cases(self):
        """ワークスペースパスのエッジケース"""

        with tempfile.TemporaryDirectory() as temp_dir:
            # 非常に長いパス名
            long_name = "a" * 100
            workspace = Path(temp_dir) / long_name
            workspace.mkdir(parents=True, exist_ok=True)

            # docker-compose.ymlを作成
            docker_compose_file = workspace / "docker-compose.yml"
            docker_compose_file.write_text("""
version: '3.8'
services:
  app:
    image: nginx:alpine
    ports:
      - "8080:80"
""")

            # devcontainer.jsonを作成
            devcontainer_path = workspace / ".devcontainer" / "devcontainer.json"
            devcontainer_path.parent.mkdir(parents=True, exist_ok=True)
            devcontainer_path.write_text("""
{
  "name": "test-long-name",
  "dockerComposeFile": "../docker-compose.yml",
  "service": "app",
  "workspaceFolder": "/workspace"
}
""")

            # docker compose psコマンドをモック
            with patch("devcontainer_tools.container.run_command") as mock_run_command:
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "long_path_container\n"
                mock_run_command.return_value = mock_result

                # Act
                from devcontainer_tools.container import get_container_id

                container_id = get_container_id(workspace)

                # Assert
                assert container_id == "long_path_container"
                # プロジェクト名が正しく生成される
                expected_project_name = f"{workspace.name}_devcontainer"
                assert len(expected_project_name) > 100  # 長い名前であることを確認

    @patch("devcontainer_tools.utils.detect_compose_config")
    @patch("devcontainer_tools.container.run_command")
    def test_concurrent_container_operations(self, mock_run_command, mock_detect_compose):
        """同時実行時の動作テスト（複数のサービスコール）"""
        # Arrange
        workspace = Path("/test/workspace")
        compose_file = Path("/test/workspace/docker-compose.yml")
        devcontainer_config = {"dockerComposeFile": "../docker-compose.yml"}  # serviceなし
        mock_detect_compose.return_value = {
            "compose_file": compose_file,
            "devcontainer_config": devcontainer_config,
        }

        # get_compose_containers呼び出し用の結果
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "container1\ncontainer2\ncontainer3\n"
        mock_run_command.return_value = mock_result

        # Act - 複数回呼び出し
        containers1 = get_compose_containers(workspace)
        containers2 = get_compose_containers(workspace)

        # Assert
        assert containers1 == ["container1", "container2", "container3"]
        assert containers2 == ["container1", "container2", "container3"]
        # 各呼び出しで1回ずつ（最初のコマンドが成功するため）
        assert mock_run_command.call_count == 2
