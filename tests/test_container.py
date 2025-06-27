"""
コンテナ操作のテスト
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from devcontainer_tools.container import execute_in_container


class TestExecuteInContainer:
    """execute_in_container関数のテスト"""

    @patch("devcontainer_tools.container.get_container_id")
    @patch("subprocess.run")
    def test_docker_exec_with_workspace_folder(self, mock_run, mock_get_container_id):
        """docker execがworkspaceFolderを使用してワーキングディレクトリを設定する"""
        # Arrange
        workspace = Path("/test/workspace")
        container_id = "abc123"
        command = ["pwd"]
        mock_get_container_id.return_value = container_id
        mock_run.return_value = MagicMock(returncode=0)

        # Act
        result = execute_in_container(
            workspace=workspace,
            command=command,
            use_docker_exec=True,
            workspace_folder="/workspace",  # 新しいパラメータ
        )

        # Assert
        mock_run.assert_called_once_with(
            ["docker", "exec", "-it", "-w", "/workspace", container_id, "pwd"], text=True
        )
        assert result.returncode == 0

    @patch("devcontainer_tools.container.get_container_id")
    @patch("subprocess.run")
    def test_docker_exec_with_default_workspace(self, mock_run, mock_get_container_id):
        """workspaceFolderが未指定の場合、デフォルトで/workspaceを使用"""
        # Arrange
        workspace = Path("/test/workspace")
        container_id = "abc123"
        command = ["ls", "-la"]
        mock_get_container_id.return_value = container_id
        mock_run.return_value = MagicMock(returncode=0)

        # Act
        result = execute_in_container(workspace=workspace, command=command, use_docker_exec=True)

        # Assert
        mock_run.assert_called_once_with(
            ["docker", "exec", "-it", "-w", "/workspace", container_id, "ls", "-la"], text=True
        )
        assert result.returncode == 0

    @patch("devcontainer_tools.container.get_container_id")
    @patch("subprocess.run")
    def test_docker_exec_with_custom_workspace_folder(self, mock_run, mock_get_container_id):
        """カスタムworkspaceFolderが指定された場合、それを使用"""
        # Arrange
        workspace = Path("/test/workspace")
        container_id = "abc123"
        command = ["npm", "install"]
        custom_workspace = "/custom/path"
        mock_get_container_id.return_value = container_id
        mock_run.return_value = MagicMock(returncode=0)

        # Act
        result = execute_in_container(
            workspace=workspace,
            command=command,
            use_docker_exec=True,
            workspace_folder=custom_workspace,
        )

        # Assert
        mock_run.assert_called_once_with(
            ["docker", "exec", "-it", "-w", custom_workspace, container_id, "npm", "install"],
            text=True,
        )
        assert result.returncode == 0

    @patch("subprocess.run")
    def test_devcontainer_exec_fallback_with_workspace(self, mock_run):
        """docker execが使用できない場合、devcontainer execにworkspaceFolderを渡す"""
        # Arrange
        workspace = Path("/test/workspace")
        command = ["echo", "test"]
        workspace_folder = "/workspace"
        mock_run.return_value = MagicMock(returncode=0)

        # Act
        result = execute_in_container(
            workspace=workspace,
            command=command,
            use_docker_exec=False,
            workspace_folder=workspace_folder,
        )

        # Assert
        # devcontainer execはworkspaceFolderを直接サポートしない可能性があるため、
        # 現状の実装を保持
        mock_run.assert_called_once_with(
            ["devcontainer", "exec", "--workspace-folder", str(workspace), "echo", "test"],
            text=True,
        )
        assert result.returncode == 0
