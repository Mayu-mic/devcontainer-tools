"""
コンテナ操作のテスト
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from devcontainer_tools.container import execute_in_container


class TestExecuteInContainer:
    """execute_in_container関数のテスト"""

    @patch("devcontainer_tools.container.get_workspace_folder")
    @patch("subprocess.run")
    def test_devcontainer_exec_without_ports(self, mock_run, mock_get_workspace_folder):
        """ポート指定なしでdevcontainer execを使用"""
        # Arrange
        workspace = Path("/test/workspace")
        command = ["pwd"]
        mock_run.return_value = MagicMock(returncode=0)
        mock_get_workspace_folder.return_value = "/workspaces/my-project"

        # Act
        result = execute_in_container(
            workspace=workspace,
            command=command,
        )

        # Assert
        mock_run.assert_called_once_with(
            ["devcontainer", "exec", "--workspace-folder", "/workspaces/my-project", "pwd"],
            text=True,
        )
        assert result.returncode == 0

    @patch("devcontainer_tools.container.get_workspace_folder")
    @patch("devcontainer_tools.container.merge_configurations_for_exec")
    @patch("subprocess.run")
    @patch("tempfile.NamedTemporaryFile")
    @patch("os.unlink")
    @patch("pathlib.Path.exists")
    def test_devcontainer_exec_with_ports(
        self,
        mock_path_exists,
        mock_unlink,
        mock_tempfile,
        mock_run,
        mock_merge_config,
        mock_get_workspace_folder,
    ):
        """ポート指定ありでdevcontainer execを使用し、一時設定ファイルを作成"""
        # Arrange
        workspace = Path("/test/workspace")
        command = ["npm", "start"]
        additional_ports = ["3000:3000", "8080:80"]
        mock_run.return_value = MagicMock(returncode=0)
        mock_get_workspace_folder.return_value = "/test/workspace"

        # 一時ファイルのモック
        temp_file = MagicMock()
        temp_file.name = "/tmp/test_config.json"
        temp_file.__enter__ = MagicMock(return_value=temp_file)
        temp_file.__exit__ = MagicMock(return_value=None)
        mock_tempfile.return_value = temp_file

        # マージされた設定のモック
        merged_config = {"appPort": [3000, 8080]}
        mock_merge_config.return_value = merged_config

        # Path.exists()をTrueに設定
        mock_path_exists.return_value = True

        # Act
        result = execute_in_container(
            workspace=workspace,
            command=command,
            additional_ports=additional_ports,
        )

        # Assert
        mock_merge_config.assert_called_once_with(workspace, additional_ports)
        mock_tempfile.assert_called_once_with(
            mode="w", suffix=".json", delete=False, dir=tempfile.gettempdir()
        )
        # ファイルへの書き込みを確認
        mock_run.assert_called_once_with(
            [
                "devcontainer",
                "exec",
                "--workspace-folder",
                str(workspace),
                "--override-config",
                temp_file.name,
                "npm",
                "start",
            ],
            text=True,
        )
        mock_unlink.assert_called_once_with(temp_file.name)
        assert result.returncode == 0

    @patch("devcontainer_tools.container.get_workspace_folder")
    @patch("devcontainer_tools.container.ensure_container_running")
    @patch("subprocess.run")
    def test_auto_up_functionality(self, mock_run, mock_ensure_running, mock_get_workspace_folder):
        """auto_up=Trueの場合、コンテナが起動していなければ自動起動"""
        # Arrange
        workspace = Path("/test/workspace")
        command = ["echo", "test"]
        mock_run.return_value = MagicMock(returncode=0)
        mock_ensure_running.return_value = True
        mock_get_workspace_folder.return_value = "/workspaces/test"

        # Act
        result = execute_in_container(
            workspace=workspace,
            command=command,
            auto_up=True,
        )

        # Assert
        mock_ensure_running.assert_called_once_with(workspace)
        mock_run.assert_called_once_with(
            ["devcontainer", "exec", "--workspace-folder", "/workspaces/test", "echo", "test"],
            text=True,
        )
        assert result.returncode == 0

    @patch("devcontainer_tools.container.merge_configurations_for_exec")
    @patch("subprocess.run")
    @patch("tempfile.NamedTemporaryFile")
    @patch("os.unlink")
    @patch("pathlib.Path.exists")
    def test_devcontainer_exec_with_single_port(
        self, mock_path_exists, mock_unlink, mock_tempfile, mock_run, mock_merge_config
    ):
        """単一ポート指定でdevcontainer execを使用"""
        # Arrange
        workspace = Path("/test/workspace")
        command = ["python", "app.py"]
        additional_ports = ["5000:5000"]
        mock_run.return_value = MagicMock(returncode=0)

        # 一時ファイルのモック
        temp_file = MagicMock()
        temp_file.name = "/tmp/test_config2.json"
        temp_file.__enter__ = MagicMock(return_value=temp_file)
        temp_file.__exit__ = MagicMock(return_value=None)
        mock_tempfile.return_value = temp_file

        # マージされた設定のモック
        merged_config = {"appPort": [5000]}
        mock_merge_config.return_value = merged_config

        # Path.exists()をTrueに設定
        mock_path_exists.return_value = True

        # Act
        result = execute_in_container(
            workspace=workspace,
            command=command,
            additional_ports=additional_ports,
        )

        # Assert
        mock_merge_config.assert_called_once_with(workspace, additional_ports)
        assert result.returncode == 0

    @patch("devcontainer_tools.container.get_workspace_folder")
    @patch("subprocess.run")
    def test_devcontainer_exec_without_auto_up(self, mock_run, mock_get_workspace_folder):
        """auto_up=Falseの場合、コンテナの自動起動はしない"""
        # Arrange
        workspace = Path("/test/workspace")
        command = ["ls", "-la"]
        mock_run.return_value = MagicMock(returncode=0)
        mock_get_workspace_folder.return_value = "/workspaces/test"

        # Act
        result = execute_in_container(
            workspace=workspace,
            command=command,
            auto_up=False,
        )

        # Assert
        mock_run.assert_called_once_with(
            ["devcontainer", "exec", "--workspace-folder", "/workspaces/test", "ls", "-la"],
            text=True,
        )
        assert result.returncode == 0

    @patch("json.dump")
    @patch("devcontainer_tools.container.merge_configurations_for_exec")
    @patch("subprocess.run")
    @patch("tempfile.NamedTemporaryFile")
    @patch("os.unlink")
    @patch("pathlib.Path.exists")
    def test_config_json_content(
        self,
        mock_path_exists,
        mock_unlink,
        mock_tempfile,
        mock_run,
        mock_merge_config,
        mock_json_dump,
    ):
        """一時設定ファイルに正しいJSON内容が書き込まれることを確認"""
        # Arrange
        workspace = Path("/test/workspace")
        command = ["node", "server.js"]
        additional_ports = ["3000:3000"]
        mock_run.return_value = MagicMock(returncode=0)

        # 一時ファイルのモック
        temp_file = MagicMock()
        temp_file.name = "/tmp/test_config3.json"
        temp_file.__enter__ = MagicMock(return_value=temp_file)
        temp_file.__exit__ = MagicMock(return_value=None)
        mock_tempfile.return_value = temp_file

        # マージされた設定のモック
        merged_config = {
            "appPort": [3000],
            "image": "node:latest",
            "mounts": ["source=.,target=/workspace,type=bind"],
        }
        mock_merge_config.return_value = merged_config

        # Path.exists()をTrueに設定
        mock_path_exists.return_value = True

        # Act
        result = execute_in_container(
            workspace=workspace,
            command=command,
            additional_ports=additional_ports,
        )

        # Assert
        mock_json_dump.assert_called_once_with(merged_config, temp_file, indent=2)
        assert result.returncode == 0

    @patch("devcontainer_tools.container.get_workspace_folder")
    @patch("subprocess.run")
    def test_exec_uses_workspace_folder_from_config(self, mock_run, mock_get_workspace_folder):
        """
        execコマンドがdevcontainer.jsonのworkspaceFolderを自動的に使用することをテスト

        期待される動作:
        - devcontainer.jsonにworkspaceFolderが定義されている場合、それを自動的に使用
        - --workspace-folderパラメータにワークスペースフォルダーを渡す
        """
        # Arrange
        workspace = Path("/test/workspace")
        command = ["pwd"]
        expected_workspace_folder = "/workspaces/my-project"
        mock_run.return_value = MagicMock(returncode=0)
        mock_get_workspace_folder.return_value = expected_workspace_folder

        # Act
        result = execute_in_container(
            workspace=workspace,
            command=command,
        )

        # Assert
        mock_get_workspace_folder.assert_called_once_with(workspace)
        mock_run.assert_called_once_with(
            ["devcontainer", "exec", "--workspace-folder", expected_workspace_folder, "pwd"],
            text=True,
        )
        assert result.returncode == 0

    @patch("devcontainer_tools.container.get_workspace_folder")
    @patch("subprocess.run")
    def test_exec_fallback_to_default_workspace_folder(self, mock_run, mock_get_workspace_folder):
        """
        execコマンドでworkspaceFolderが取得できない場合のフォールバック動作をテスト

        期待される動作:
        - get_workspace_folderが例外を投げた場合、デフォルトの.を使用
        """
        # Arrange
        workspace = Path("/test/workspace")
        command = ["pwd"]
        mock_run.return_value = MagicMock(returncode=0)
        mock_get_workspace_folder.side_effect = Exception("Config not found")

        # Act
        result = execute_in_container(
            workspace=workspace,
            command=command,
        )

        # Assert
        mock_get_workspace_folder.assert_called_once_with(workspace)
        # エラーが発生した場合、デフォルトの.が使用される
        mock_run.assert_called_once_with(
            ["devcontainer", "exec", "--workspace-folder", ".", "pwd"], text=True
        )
        assert result.returncode == 0

    @patch("devcontainer_tools.container.get_workspace_folder")
    @patch("devcontainer_tools.container.merge_configurations_for_exec")
    @patch("subprocess.run")
    @patch("tempfile.NamedTemporaryFile")
    @patch("os.unlink")
    @patch("pathlib.Path.exists")
    def test_exec_with_ports_uses_workspace_folder_from_config(
        self,
        mock_path_exists,
        mock_unlink,
        mock_tempfile,
        mock_run,
        mock_merge_config,
        mock_get_workspace_folder,
    ):
        """
        ポート指定ありのexecコマンドでもworkspaceFolderを自動使用することをテスト
        """
        # Arrange
        workspace = Path("/test/workspace")
        command = ["npm", "start"]
        additional_ports = ["3000:3000"]
        expected_workspace_folder = "/workspaces/my-project"
        mock_run.return_value = MagicMock(returncode=0)
        mock_get_workspace_folder.return_value = expected_workspace_folder

        # 一時ファイルのモック
        temp_file = MagicMock()
        temp_file.name = "/tmp/test_config.json"
        temp_file.__enter__ = MagicMock(return_value=temp_file)
        temp_file.__exit__ = MagicMock(return_value=None)
        mock_tempfile.return_value = temp_file

        # マージされた設定のモック
        merged_config = {"appPort": [3000]}
        mock_merge_config.return_value = merged_config

        # Path.exists()をTrueに設定
        mock_path_exists.return_value = True

        # Act
        result = execute_in_container(
            workspace=workspace,
            command=command,
            additional_ports=additional_ports,
        )

        # Assert
        mock_get_workspace_folder.assert_called_once_with(workspace)
        mock_run.assert_called_once_with(
            [
                "devcontainer",
                "exec",
                "--workspace-folder",
                expected_workspace_folder,  # ここでworkspaceFolderが使用される
                "--override-config",
                temp_file.name,
                "npm",
                "start",
            ],
            text=True,
        )
        assert result.returncode == 0
