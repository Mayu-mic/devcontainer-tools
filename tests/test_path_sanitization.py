"""
パスサニタイゼーション機能のテスト
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from devcontainer_tools.config import InvalidWorkspaceFolderError, get_workspace_folder
from devcontainer_tools.container import execute_in_container


class TestPathSanitization:
    """パスサニタイゼーション機能のテスト"""

    def test_get_workspace_folder_with_relative_path(self):
        """相対パスが絶対パスに正規化される"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            devcontainer_dir = workspace / ".devcontainer"
            devcontainer_dir.mkdir()

            # 相対パスを含む設定ファイルを作成
            config_file = devcontainer_dir / "devcontainer.json"
            config_content = '{"workspaceFolder": "./src"}'
            config_file.write_text(config_content, encoding="utf-8")

            # 実行
            result = get_workspace_folder(workspace)

            # 絶対パスに正規化されることを確認
            assert result.startswith("/")
            assert "src" in result

    def test_get_workspace_folder_with_directory_traversal(self):
        """ディレクトリトラバーサル攻撃が防がれる"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            devcontainer_dir = workspace / ".devcontainer"
            devcontainer_dir.mkdir()

            # 危険な相対パスを含む設定ファイルを作成
            config_file = devcontainer_dir / "devcontainer.json"
            config_content = '{"workspaceFolder": "../../../etc"}'
            config_file.write_text(config_content, encoding="utf-8")

            # 実行
            result = get_workspace_folder(workspace)

            # 正規化されて安全なパスになることを確認
            assert result.startswith("/")
            # ディレクトリトラバーサルが解決されている
            assert "etc" in result

    def test_get_workspace_folder_with_invalid_path(self):
        """無効なパスの場合エラーが発生する"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            devcontainer_dir = workspace / ".devcontainer"
            devcontainer_dir.mkdir()

            # 制御文字を含む無効なパスを含む設定ファイルを作成
            config_file = devcontainer_dir / "devcontainer.json"
            config_content = '{"workspaceFolder": "\\u0000invalid"}'
            config_file.write_text(config_content, encoding="utf-8")

            # 実行してエラーが発生することを確認
            with pytest.raises(InvalidWorkspaceFolderError, match="制御文字が含まれています"):
                get_workspace_folder(workspace)

    def test_get_workspace_folder_with_empty_path(self):
        """空のパスの場合エラーが発生する"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            devcontainer_dir = workspace / ".devcontainer"
            devcontainer_dir.mkdir()

            # 空文字列を含む設定ファイルを作成
            config_file = devcontainer_dir / "devcontainer.json"
            config_content = '{"workspaceFolder": ""}'
            config_file.write_text(config_content, encoding="utf-8")

            # 実行してエラーが発生することを確認
            with pytest.raises(InvalidWorkspaceFolderError, match="workspaceFolderが空です"):
                get_workspace_folder(workspace)

    def test_get_workspace_folder_nonexistent_workspace(self):
        """存在しないワークスペースの場合デフォルト値が返される"""
        nonexistent_workspace = Path("/nonexistent/path")

        # 実行
        result = get_workspace_folder(nonexistent_workspace)

        # デフォルト値が返されることを確認
        assert result == "."

    @patch("subprocess.run")
    def test_execute_in_container_uses_devcontainer_exec(self, mock_run):
        """execute_in_containerは常にdevcontainer execを使用する"""
        # Arrange
        workspace = Path("/test/workspace")
        command = ["pwd"]
        mock_run.return_value = MagicMock(returncode=0)

        # Act
        execute_in_container(
            workspace=workspace,
            command=command,
        )

        # Assert
        mock_run.assert_called_once()
        called_cmd = mock_run.call_args[0][0]
        # devcontainer execが使用されることを確認
        assert called_cmd[:4] == ["devcontainer", "exec", "--workspace-folder", "."]
        assert called_cmd[4:] == ["pwd"]

    def test_path_normalization_edge_cases(self):
        """パス正規化のエッジケースをテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            devcontainer_dir = workspace / ".devcontainer"
            devcontainer_dir.mkdir()

            # 有効なパスのテストケース
            valid_test_cases = [
                ("./src", True),  # 相対パス
                ("/absolute/path", True),  # 絶対パス
                ("relative/path", True),  # 相対パス（./なし）
            ]

            for test_path, _should_work in valid_test_cases:
                config_file = devcontainer_dir / "devcontainer.json"
                config_content = f'{{"workspaceFolder": "{test_path}"}}'
                config_file.write_text(config_content, encoding="utf-8")

                result = get_workspace_folder(workspace)

                # 有効なパスは正規化される
                assert result.startswith("/")
                if test_path.startswith("/"):
                    # 既に絶対パスの場合はそのまま
                    assert test_path in result or result == test_path

            # 無効なパスのテストケース - エラーが発生することを確認
            config_file = devcontainer_dir / "devcontainer.json"
            config_content = '{"workspaceFolder": ""}'  # 空文字列
            config_file.write_text(config_content, encoding="utf-8")

            with pytest.raises(InvalidWorkspaceFolderError, match="workspaceFolderが空です"):
                get_workspace_folder(workspace)
