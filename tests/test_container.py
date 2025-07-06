"""
コンテナ操作のテスト
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from devcontainer_tools.container import (
    _get_error_message,
    _truncate_output,
    ensure_container_running,
    execute_in_container,
    get_compose_containers,
    is_compose_project,
    run_command,
    stop_and_remove_compose_containers,
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


class TestHelperFunctions:
    """ヘルパー関数のテスト"""

    def test_truncate_output_short_text(self):
        """短いテキストの切り詰めテスト"""
        text = "short text"
        result = _truncate_output(text)
        assert result == "short text"

    def test_truncate_output_long_text(self):
        """長いテキストの切り詰めテスト"""
        text = "a" * 250
        result = _truncate_output(text)
        assert result == "a" * 200 + "..."
        assert len(result) == 203

    def test_truncate_output_custom_length(self):
        """カスタム長さでの切り詰めテスト"""
        text = "a" * 150
        result = _truncate_output(text, max_length=100)
        assert result == "a" * 100 + "..."

    def test_get_error_message_stderr_priority(self):
        """stderr優先のエラーメッセージテスト"""
        result = MagicMock()
        result.stderr = "stderr message"
        result.stdout = "stdout message"
        result.returncode = 1

        error_msg = _get_error_message(result)
        assert error_msg == "stderr message"

    def test_get_error_message_stdout_fallback(self):
        """stdout代替のエラーメッセージテスト"""
        result = MagicMock()
        result.stderr = ""
        result.stdout = "stdout message"
        result.returncode = 1

        error_msg = _get_error_message(result)
        assert error_msg == "stdout message"

    def test_get_error_message_returncode_fallback(self):
        """終了コード代替のエラーメッセージテスト"""
        result = MagicMock()
        result.stderr = ""
        result.stdout = ""
        result.returncode = 127

        error_msg = _get_error_message(result)
        assert error_msg == "プロセス終了コード: 127"

    def test_get_error_message_with_whitespace(self):
        """空白文字を含むエラーメッセージのテスト"""
        result = MagicMock()
        result.stderr = "  error with spaces  "
        result.stdout = ""
        result.returncode = 1

        error_msg = _get_error_message(result)
        assert error_msg == "error with spaces"


class TestDockerComposeSupport:
    """Docker Compose対応のテスト"""

    def test_is_compose_project_with_compose_file(self):
        """docker-compose.ymlがある場合のテスト"""
        import tempfile

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

            result = is_compose_project(workspace)
            assert result is True

    def test_is_compose_project_without_compose_file(self):
        """docker-compose.ymlがない場合のテスト"""
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            # Create only devcontainer.json without dockerComposeFile
            devcontainer_path = workspace / ".devcontainer" / "devcontainer.json"
            devcontainer_path.parent.mkdir(parents=True, exist_ok=True)
            devcontainer_path.write_text('{"name": "test", "image": "ubuntu:20.04"}')

            result = is_compose_project(workspace)
            assert result is False

    def test_is_compose_project_no_devcontainer_json(self):
        """devcontainer.jsonがない場合のテスト"""
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            result = is_compose_project(workspace)
            assert result is False

    @patch("devcontainer_tools.utils.detect_compose_config")
    @patch("devcontainer_tools.container.run_command")
    def test_get_compose_containers_success(self, mock_run_command, mock_detect_compose):
        """compose コンテナ取得成功のテスト"""
        # Arrange
        workspace = Path("/test/workspace")
        compose_file = Path("/test/workspace/docker-compose.yml")
        mock_detect_compose.return_value = {"compose_file": compose_file}

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "container1\ncontainer2\ncontainer3\n"
        mock_run_command.return_value = mock_result

        # Act
        containers = get_compose_containers(workspace)

        # Assert
        assert containers == ["container1", "container2", "container3"]
        mock_run_command.assert_called_once_with(
            ["docker", "compose", "-f", str(compose_file), "ps", "-q"], check=False
        )

    @patch("devcontainer_tools.utils.detect_compose_config")
    @patch("devcontainer_tools.container.run_command")
    def test_get_compose_containers_failure(self, mock_run_command, mock_detect_compose):
        """compose コンテナ取得失敗のテスト"""
        # Arrange
        workspace = Path("/test/workspace")
        compose_file = Path("/test/workspace/docker-compose.yml")
        mock_detect_compose.return_value = {"compose_file": compose_file}

        # 両方のコマンドが失敗する場合
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_run_command.return_value = mock_result

        # Act
        containers = get_compose_containers(workspace)

        # Assert
        assert containers == []
        # 2回呼び出される（通常のコマンドとdevcontainerプロジェクト名付きのコマンド）
        assert mock_run_command.call_count == 2

    @patch("devcontainer_tools.utils.detect_compose_config")
    @patch("devcontainer_tools.container.run_command")
    def test_get_compose_containers_empty(self, mock_run_command, mock_detect_compose):
        """compose コンテナが空の場合のテスト"""
        # Arrange
        workspace = Path("/test/workspace")
        compose_file = Path("/test/workspace/docker-compose.yml")
        mock_detect_compose.return_value = {"compose_file": compose_file}

        # 両方のコマンドが空の結果を返す場合
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_run_command.return_value = mock_result

        # Act
        containers = get_compose_containers(workspace)

        # Assert
        assert containers == []
        # 2回呼び出される（通常のコマンドとdevcontainerプロジェクト名付きのコマンド）
        assert mock_run_command.call_count == 2

    @patch("devcontainer_tools.utils.detect_compose_config")
    @patch("devcontainer_tools.container.run_command")
    def test_stop_and_remove_compose_containers_success(
        self, mock_run_command, mock_detect_compose
    ):
        """compose コンテナ停止・削除成功のテスト"""
        # Arrange
        workspace = Path("/test/workspace")
        compose_file = Path("/test/workspace/docker-compose.yml")
        mock_detect_compose.return_value = {"compose_file": compose_file}

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run_command.return_value = mock_result

        # Act
        result = stop_and_remove_compose_containers(workspace, remove_volumes=False)

        # Assert
        assert result is True
        mock_run_command.assert_called_once_with(
            ["docker", "compose", "-f", str(compose_file), "down"], check=False, verbose=True
        )

    @patch("devcontainer_tools.utils.detect_compose_config")
    @patch("devcontainer_tools.container.run_command")
    def test_stop_and_remove_compose_containers_with_volumes(
        self, mock_run_command, mock_detect_compose
    ):
        """compose コンテナ停止・削除（ボリューム付き）のテスト"""
        # Arrange
        workspace = Path("/test/workspace")
        compose_file = Path("/test/workspace/docker-compose.yml")
        mock_detect_compose.return_value = {"compose_file": compose_file}

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run_command.return_value = mock_result

        # Act
        result = stop_and_remove_compose_containers(workspace, remove_volumes=True)

        # Assert
        assert result is True
        mock_run_command.assert_called_once_with(
            ["docker", "compose", "-f", str(compose_file), "down", "-v"], check=False, verbose=True
        )

    @patch("devcontainer_tools.utils.detect_compose_config")
    @patch("devcontainer_tools.container.run_command")
    def test_stop_and_remove_compose_containers_failure(
        self, mock_run_command, mock_detect_compose
    ):
        """compose コンテナ停止・削除失敗のテスト"""
        # Arrange
        workspace = Path("/test/workspace")
        compose_file = Path("/test/workspace/docker-compose.yml")
        mock_detect_compose.return_value = {"compose_file": compose_file}

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Docker compose down failed"
        mock_run_command.return_value = mock_result

        # Act
        result = stop_and_remove_compose_containers(workspace, remove_volumes=False)

        # Assert
        assert result is False
        mock_run_command.assert_called_once_with(
            ["docker", "compose", "-f", str(compose_file), "down"], check=False, verbose=True
        )

    @patch("devcontainer_tools.utils.detect_compose_config")
    def test_stop_and_remove_compose_containers_exception(self, mock_detect_compose):
        """compose コンテナ停止・削除中に例外が発生するテスト"""
        # Arrange
        workspace = Path("/test/workspace")
        mock_detect_compose.side_effect = Exception("Unexpected error")

        # Act
        result = stop_and_remove_compose_containers(workspace, remove_volumes=False)

        # Assert
        assert result is False


class TestGetContainerIdForDockerCompose:
    """docker-compose環境でのget_container_id関数のテスト"""

    @patch("devcontainer_tools.utils.detect_compose_config")
    @patch("devcontainer_tools.container.run_command")
    def test_get_container_id_docker_compose_with_service(
        self, mock_run_command, mock_detect_compose
    ):
        """docker-compose環境でサービス名が指定されている場合のコンテナID取得"""
        # Arrange
        workspace = Path("/test/workspace")
        compose_file = Path("/test/workspace/docker-compose.yml")
        devcontainer_config = {"service": "app", "dockerComposeFile": "../docker-compose.yml"}
        mock_detect_compose.return_value = {
            "compose_file": compose_file,
            "devcontainer_config": devcontainer_config,
        }

        # docker compose ps -q app コマンドの結果をモック
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "container123\n"
        mock_run_command.return_value = mock_result

        # Act
        from devcontainer_tools.container import get_container_id

        container_id = get_container_id(workspace)

        # Assert
        assert container_id == "container123"
        mock_run_command.assert_called_once_with(
            ["docker", "compose", "-f", str(compose_file), "ps", "-q", "app"], check=False
        )

    @patch("devcontainer_tools.utils.detect_compose_config")
    @patch("devcontainer_tools.container.run_command")
    def test_get_container_id_docker_compose_without_service(
        self, mock_run_command, mock_detect_compose
    ):
        """docker-compose環境でサービス名が指定されていない場合のコンテナID取得"""
        # Arrange
        workspace = Path("/test/workspace")
        compose_file = Path("/test/workspace/docker-compose.yml")
        devcontainer_config = {"dockerComposeFile": "../docker-compose.yml"}  # serviceなし
        mock_detect_compose.return_value = {
            "compose_file": compose_file,
            "devcontainer_config": devcontainer_config,
        }

        # docker compose ps -q コマンドの結果をモック（全コンテナ取得）
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "container123\ncontainer456\n"
        mock_run_command.return_value = mock_result

        # Act
        from devcontainer_tools.container import get_container_id

        container_id = get_container_id(workspace)

        # Assert
        assert container_id == "container123"  # 最初のコンテナを取得
        mock_run_command.assert_called_once_with(
            ["docker", "compose", "-f", str(compose_file), "ps", "-q"], check=False
        )

    @patch("devcontainer_tools.utils.detect_compose_config")
    @patch("devcontainer_tools.container.run_command")
    def test_get_container_id_docker_compose_no_containers(
        self, mock_run_command, mock_detect_compose
    ):
        """docker-compose環境でコンテナが見つからない場合"""
        # Arrange
        workspace = Path("/test/workspace")
        compose_file = Path("/test/workspace/docker-compose.yml")
        devcontainer_config = {"service": "app", "dockerComposeFile": "../docker-compose.yml"}
        mock_detect_compose.return_value = {
            "compose_file": compose_file,
            "devcontainer_config": devcontainer_config,
        }

        # 両方のコマンドが空の結果を返す場合
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_run_command.return_value = mock_result

        # Act
        from devcontainer_tools.container import get_container_id

        container_id = get_container_id(workspace)

        # Assert
        assert container_id is None
        # 2回呼び出される（通常のコマンドとdevcontainerプロジェクト名付きのコマンド）
        assert mock_run_command.call_count == 2

    @patch("devcontainer_tools.utils.detect_compose_config")
    @patch("devcontainer_tools.container.run_command")
    def test_get_container_id_docker_compose_command_failure(
        self, mock_run_command, mock_detect_compose
    ):
        """docker-compose環境でコマンドが失敗した場合"""
        # Arrange
        workspace = Path("/test/workspace")
        compose_file = Path("/test/workspace/docker-compose.yml")
        devcontainer_config = {"service": "app", "dockerComposeFile": "../docker-compose.yml"}
        mock_detect_compose.return_value = {
            "compose_file": compose_file,
            "devcontainer_config": devcontainer_config,
        }

        # 両方のコマンドが失敗する場合
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_run_command.return_value = mock_result

        # Act
        from devcontainer_tools.container import get_container_id

        container_id = get_container_id(workspace)

        # Assert
        assert container_id is None
        # 2回呼び出される（通常のコマンドとdevcontainerプロジェクト名付きのコマンド）
        assert mock_run_command.call_count == 2
