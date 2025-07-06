"""
コンテナ操作の統合テスト
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from devcontainer_tools.container import get_container_id


class TestDockerComposeContainerIntegration:
    """docker-compose環境での統合テスト"""

    def test_get_container_id_docker_compose_integration(self):
        """docker-compose環境での統合テスト（実際のファイル使用）"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            # docker-compose.ymlを作成
            docker_compose_file = workspace / "docker-compose.yml"
            docker_compose_file.write_text("""
version: '3.8'
services:
  app:
    build: .
    ports:
      - "3000:3000"
  db:
    image: postgres:13
    environment:
      POSTGRES_DB: testdb
""")

            # devcontainer.jsonを作成
            devcontainer_path = workspace / ".devcontainer" / "devcontainer.json"
            devcontainer_path.parent.mkdir(parents=True, exist_ok=True)
            devcontainer_path.write_text("""
{
  "name": "test-compose",
  "dockerComposeFile": "../docker-compose.yml",
  "service": "app",
  "workspaceFolder": "/workspace"
}
""")

            # docker compose psコマンドをモック
            with patch("devcontainer_tools.container.run_command") as mock_run_command:
                # docker compose ps -q app コマンドの結果をモック
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "container123abc\n"
                mock_run_command.return_value = mock_result

                # Act
                container_id = get_container_id(workspace)

                # Assert
                assert container_id == "container123abc"
                # パスの正規化を考慮してコマンドを確認
                called_args = mock_run_command.call_args[0][0]
                assert called_args[0] == "docker"
                assert called_args[1] == "compose"
                assert called_args[2] == "-f"
                assert called_args[3].endswith("docker-compose.yml")
                assert called_args[4] == "ps"
                assert called_args[5] == "-q"
                assert called_args[6] == "app"

    def test_get_container_id_docker_compose_without_service_integration(self):
        """docker-compose環境でサービス名がない場合の統合テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            # docker-compose.ymlを作成
            docker_compose_file = workspace / "docker-compose.yml"
            docker_compose_file.write_text("""
version: '3.8'
services:
  app:
    build: .
    ports:
      - "3000:3000"
  db:
    image: postgres:13
    environment:
      POSTGRES_DB: testdb
""")

            # devcontainer.jsonを作成（serviceプロパティなし）
            devcontainer_path = workspace / ".devcontainer" / "devcontainer.json"
            devcontainer_path.parent.mkdir(parents=True, exist_ok=True)
            devcontainer_path.write_text("""
{
  "name": "test-compose",
  "dockerComposeFile": "../docker-compose.yml",
  "workspaceFolder": "/workspace"
}
""")

            # docker compose psコマンドをモック
            with patch("devcontainer_tools.container.run_command") as mock_run_command:
                # 1回目の呼び出しで成功する場合（serviceがない場合はget_compose_containersを使用）
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "container123abc\ncontainer456def\n"
                mock_run_command.return_value = mock_result

                # Act
                container_id = get_container_id(workspace)

                # Assert
                assert container_id == "container123abc"  # 最初のコンテナを返す
                # 1回目で成功するため、1回呼び出される
                assert mock_run_command.call_count == 1
                # パスの正規化を考慮してコマンドを確認
                called_args = mock_run_command.call_args[0][0]
                assert called_args[0] == "docker"
                assert called_args[1] == "compose"
                assert called_args[2] == "-f"
                assert called_args[3].endswith("docker-compose.yml")
                assert called_args[4] == "ps"
                assert called_args[5] == "-q"

    def test_get_container_id_docker_compose_no_containers_running(self):
        """docker-compose環境でコンテナが起動していない場合の統合テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            # docker-compose.ymlを作成
            docker_compose_file = workspace / "docker-compose.yml"
            docker_compose_file.write_text("""
version: '3.8'
services:
  app:
    build: .
    ports:
      - "3000:3000"
""")

            # devcontainer.jsonを作成
            devcontainer_path = workspace / ".devcontainer" / "devcontainer.json"
            devcontainer_path.parent.mkdir(parents=True, exist_ok=True)
            devcontainer_path.write_text("""
{
  "name": "test-compose",
  "dockerComposeFile": "../docker-compose.yml",
  "service": "app",
  "workspaceFolder": "/workspace"
}
""")

            # docker compose psコマンドをモック（コンテナが起動していない）
            with patch("devcontainer_tools.container.run_command") as mock_run_command:
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = ""  # コンテナが起動していない
                mock_run_command.return_value = mock_result

                # Act
                container_id = get_container_id(workspace)

                # Assert
                assert container_id is None
                # 2回呼び出される（通常のコマンドとdevcontainerプロジェクト名付きのコマンド）
                assert mock_run_command.call_count == 2
                # 1回目のコマンドを確認
                first_call_args = mock_run_command.call_args_list[0][0][0]
                assert first_call_args[0] == "docker"
                assert first_call_args[1] == "compose"
                assert first_call_args[2] == "-f"
                assert first_call_args[3].endswith("docker-compose.yml")
                assert first_call_args[4] == "ps"
                assert first_call_args[5] == "-q"
                assert first_call_args[6] == "app"

    def test_get_container_id_non_docker_compose_environment(self):
        """非docker-compose環境でのコンテナ検出テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            # 通常のdevcontainer.jsonを作成
            devcontainer_path = workspace / ".devcontainer" / "devcontainer.json"
            devcontainer_path.parent.mkdir(parents=True, exist_ok=True)
            devcontainer_path.write_text("""
{
  "name": "test-single",
  "image": "ubuntu:20.04",
  "workspaceFolder": "/workspace"
}
""")

            # docker psコマンドをモック
            with patch("devcontainer_tools.container.run_command") as mock_run_command:
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "container789xyz\n"
                mock_run_command.return_value = mock_result

                # Act
                container_id = get_container_id(workspace)

                # Assert
                assert container_id == "container789xyz"
                mock_run_command.assert_called_once_with(
                    ["docker", "ps", "-q", "-f", f"label=devcontainer.local_folder={workspace}"],
                    check=False,
                )

    def test_get_container_id_devcontainer_project_name_issue(self):
        """devcontainerのプロジェクト名が考慮されていない問題を再現するテスト"""
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            # docker-compose.ymlを作成
            docker_compose_file = workspace / ".devcontainer" / "docker-compose.yml"
            docker_compose_file.parent.mkdir(parents=True, exist_ok=True)
            docker_compose_file.write_text("""
services:
  app:
    build: .
    ports:
      - "3000:3000"
  db:
    image: postgres:13
    ports:
      - "5432:5432"
""")

            # devcontainer.jsonを作成
            devcontainer_path = workspace / ".devcontainer" / "devcontainer.json"
            devcontainer_path.write_text("""
{
  "name": "test-compose",
  "dockerComposeFile": "docker-compose.yml",
  "service": "app",
  "workspaceFolder": "/workspace"
}
""")

            # docker composeコマンドをモック（プロジェクト名なしでは失敗）
            from unittest.mock import patch

            with patch("devcontainer_tools.container.run_command") as mock_run_command:
                # 最初のコール（プロジェクト名なし）は空の結果
                # 2番目のコール（devcontainerプロジェクト名付き）は成功
                mock_results = [
                    MagicMock(returncode=0, stdout=""),  # プロジェクト名なし -> 空
                    MagicMock(
                        returncode=0, stdout="container123abc\n"
                    ),  # devcontainerプロジェクト名付き -> 成功
                ]
                mock_run_command.side_effect = mock_results

                # Act
                container_id = get_container_id(workspace)

                # Assert
                # devcontainerプロジェクト名を試行して成功する
                assert container_id == "container123abc"

                # 2回のコマンド実行を確認
                assert mock_run_command.call_count == 2

                # 1回目: 通常のプロジェクト名
                first_call = mock_run_command.call_args_list[0]
                assert first_call[0][0][0] == "docker"
                assert first_call[0][0][1] == "compose"
                assert first_call[0][0][2] == "-f"
                assert first_call[0][0][3].endswith("docker-compose.yml")
                assert first_call[0][0][4] == "ps"
                assert first_call[0][0][5] == "-q"
                assert first_call[0][0][6] == "app"

                # 2回目: devcontainerプロジェクト名付き
                second_call = mock_run_command.call_args_list[1]
                assert second_call[0][0][0] == "docker"
                assert second_call[0][0][1] == "compose"
                assert second_call[0][0][2] == "--project-name"
                # プロジェクト名は {workspace_name}_devcontainer 形式
                expected_project_name = f"{workspace.name}_devcontainer"
                assert second_call[0][0][3] == expected_project_name
                assert second_call[0][0][4] == "-f"
                assert second_call[0][0][5].endswith("docker-compose.yml")
                assert second_call[0][0][6] == "ps"
                assert second_call[0][0][7] == "-q"
                assert second_call[0][0][8] == "app"
