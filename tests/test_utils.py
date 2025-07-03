"""Tests for utility functions module."""

import json
import tempfile
from pathlib import Path

from devcontainer_tools.utils import (
    detect_compose_config,
    find_devcontainer_json,
    load_json_file,
    parse_mount_string,
    save_json_file,
)


class TestLoadJsonFile:
    """Test the load_json_file function."""

    def test_load_valid_json(self):
        """Test loading a valid JSON file."""
        test_data = {"name": "test", "version": "1.0"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            file_path = Path(f.name)

        try:
            result = load_json_file(file_path)
            assert result == test_data
        finally:
            file_path.unlink()

    def test_load_nonexistent_file(self):
        """Test loading a non-existent file returns empty dict."""
        non_existent = Path("/non/existent/file.json")
        result = load_json_file(non_existent)
        assert result == {}

    def test_load_invalid_json(self):
        """Test loading invalid JSON returns empty dict."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json }")
            file_path = Path(f.name)

        try:
            result = load_json_file(file_path)
            assert result == {}
        finally:
            file_path.unlink()

    def test_load_empty_file(self):
        """Test loading an empty file returns empty dict."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("")
            file_path = Path(f.name)

        try:
            result = load_json_file(file_path)
            assert result == {}
        finally:
            file_path.unlink()


class TestFindDevcontainerJson:
    """Test the find_devcontainer_json function."""

    def test_find_in_devcontainer_dir(self):
        """Test finding devcontainer.json in .devcontainer directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            devcontainer_dir = workspace / ".devcontainer"
            devcontainer_dir.mkdir()

            config_file = devcontainer_dir / "devcontainer.json"
            config_file.write_text('{"name": "test"}')

            result = find_devcontainer_json(workspace)
            assert result == config_file

    def test_find_in_root_dir(self):
        """Test finding devcontainer.json in root directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            config_file = workspace / "devcontainer.json"
            config_file.write_text('{"name": "test"}')

            result = find_devcontainer_json(workspace)
            assert result == config_file

    def test_prefer_devcontainer_dir(self):
        """Test that .devcontainer/devcontainer.json is preferred over root."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            # Create both files
            devcontainer_dir = workspace / ".devcontainer"
            devcontainer_dir.mkdir()

            preferred_file = devcontainer_dir / "devcontainer.json"
            preferred_file.write_text('{"name": "preferred"}')

            root_file = workspace / "devcontainer.json"
            root_file.write_text('{"name": "root"}')

            result = find_devcontainer_json(workspace)
            assert result == preferred_file

    def test_find_nothing(self):
        """Test when no devcontainer.json is found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            result = find_devcontainer_json(workspace)
            assert result is None


class TestParseMountString:
    """Test the parse_mount_string function."""

    def test_parse_complete_mount_string(self):
        """Test parsing a complete mount string."""
        mount_str = "source=/host,target=/container,type=bind,consistency=cached"
        result = parse_mount_string(mount_str)
        assert result == mount_str

    def test_parse_simple_mount_string(self):
        """Test parsing a simple host:container mount string."""
        mount_str = "/host/path:/container/path"
        result = parse_mount_string(mount_str)
        expected = "source=/host/path,target=/container/path,type=bind,consistency=cached"
        assert result == expected

    def test_parse_invalid_mount_string(self):
        """Test parsing an invalid mount string returns original."""
        mount_str = "invalid_mount_format"
        result = parse_mount_string(mount_str)
        assert result == mount_str

    def test_parse_empty_mount_string(self):
        """Test parsing an empty mount string."""
        mount_str = ""
        result = parse_mount_string(mount_str)
        assert result == ""


class TestSaveJsonFile:
    """Test the save_json_file function."""

    def test_save_valid_data(self):
        """Test saving valid JSON data."""
        test_data = {"name": "test", "version": "1.0"}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.json"
            result = save_json_file(test_data, file_path)

            assert result is True
            assert file_path.exists()

            # Verify content
            loaded_data = load_json_file(file_path)
            assert loaded_data == test_data

    def test_save_creates_directory(self):
        """Test that save_json_file creates parent directories."""
        test_data = {"test": "data"}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "nested" / "dir" / "test.json"
            result = save_json_file(test_data, file_path)

            assert result is True
            assert file_path.exists()
            assert file_path.parent.exists()

    def test_save_with_custom_indent(self):
        """Test saving with custom indentation."""
        test_data = {"name": "test", "nested": {"key": "value"}}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.json"
            result = save_json_file(test_data, file_path, indent=4)

            assert result is True

            # Check that the file is properly indented
            content = file_path.read_text()
            assert "    " in content  # 4-space indentation

    def test_save_to_readonly_location(self):
        """Test saving to a read-only location fails gracefully."""
        test_data = {"test": "data"}
        readonly_path = Path("/root/readonly/test.json")  # Assuming no write access

        result = save_json_file(test_data, readonly_path)
        assert result is False


class TestDetectComposeConfig:
    """Test the detect_compose_config function."""

    def test_detect_compose_with_dockerComposeFile(self):
        """Test detecting compose config with dockerComposeFile in devcontainer.json."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            # Create devcontainer.json with dockerComposeFile
            devcontainer_dir = workspace / ".devcontainer"
            devcontainer_dir.mkdir()
            config_file = devcontainer_dir / "devcontainer.json"
            config_file.write_text(
                '\n{\n  "name": "test",\n  "dockerComposeFile": "../docker-compose.yml",\n  "service": "app"\n}'
            )

            # Create docker-compose.yml
            compose_file = workspace / "docker-compose.yml"
            compose_file.write_text(
                "version: '3.8'\nservices:\n  app:\n    build: .\n    ports:\n      - 3000:3000\n  db:\n    image: postgres:13"
            )

            result = detect_compose_config(workspace)
            assert result is not None
            assert result["compose_file"] == compose_file
            assert result["devcontainer_config"]["dockerComposeFile"] == "../docker-compose.yml"
            assert result["devcontainer_config"]["service"] == "app"

    def test_detect_compose_with_dockerComposeFile_array(self):
        """Test detecting compose config with dockerComposeFile as array."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            # Create devcontainer.json with dockerComposeFile as array
            devcontainer_dir = workspace / ".devcontainer"
            devcontainer_dir.mkdir()
            config_file = devcontainer_dir / "devcontainer.json"
            config_file.write_text(
                '{\n  "name": "test",\n  "dockerComposeFile": ["../docker-compose.yml", "../docker-compose.override.yml"],\n  "service": "app"\n}'
            )

            # Create docker-compose files
            compose_file = workspace / "docker-compose.yml"
            compose_file.write_text("version: '3.8'\nservices:\n  app:\n    build: .")
            compose_override = workspace / "docker-compose.override.yml"
            compose_override.write_text(
                "version: '3.8'\nservices:\n  app:\n    ports:\n      - 3000:3000"
            )

            result = detect_compose_config(workspace)
            assert result is not None
            assert result["compose_file"] == compose_file  # First file in the array
            assert result["devcontainer_config"]["dockerComposeFile"] == [
                "../docker-compose.yml",
                "../docker-compose.override.yml",
            ]
            assert result["devcontainer_config"]["service"] == "app"

    def test_detect_compose_without_dockerComposeFile(self):
        """Test detecting compose config without dockerComposeFile in devcontainer.json."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            # Create devcontainer.json without dockerComposeFile
            devcontainer_dir = workspace / ".devcontainer"
            devcontainer_dir.mkdir()
            config_file = devcontainer_dir / "devcontainer.json"
            config_file.write_text('{\n  "name": "test",\n  "image": "ubuntu:20.04"\n}')

            result = detect_compose_config(workspace)
            assert result is None

    def test_detect_compose_nonexistent_compose_file(self):
        """Test detecting compose config when compose file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            # Create devcontainer.json with dockerComposeFile but no actual compose file
            devcontainer_dir = workspace / ".devcontainer"
            devcontainer_dir.mkdir()
            config_file = devcontainer_dir / "devcontainer.json"
            config_file.write_text(
                '{\n  "name": "test",\n  "dockerComposeFile": "../docker-compose.yml",\n  "service": "app"\n}'
            )

            # Don't create docker-compose.yml

            result = detect_compose_config(workspace)
            assert result is None

    def test_detect_compose_no_devcontainer_json(self):
        """Test detecting compose config when devcontainer.json doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            result = detect_compose_config(workspace)
            assert result is None

    def test_detect_compose_with_relative_path(self):
        """Test detecting compose config with various relative paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            # Create nested directory structure
            nested_dir = workspace / "nested"
            nested_dir.mkdir()
            devcontainer_dir = nested_dir / ".devcontainer"
            devcontainer_dir.mkdir()

            # Create devcontainer.json with relative path to compose file
            config_file = devcontainer_dir / "devcontainer.json"
            config_file.write_text(
                '{\n  "name": "test",\n  "dockerComposeFile": "../../docker-compose.yml",\n  "service": "app"\n}'
            )

            # Create docker-compose.yml at workspace root
            compose_file = workspace / "docker-compose.yml"
            compose_file.write_text("version: '3.8'\nservices:\n  app:\n    build: .")

            result = detect_compose_config(nested_dir)
            assert result is not None
            assert result["compose_file"] == compose_file
            assert result["devcontainer_config"]["dockerComposeFile"] == "../../docker-compose.yml"

    def test_detect_compose_with_absolute_path(self):
        """Test detecting compose config with absolute path (should be rejected)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            # Create devcontainer.json with absolute path
            devcontainer_dir = workspace / ".devcontainer"
            devcontainer_dir.mkdir()
            config_file = devcontainer_dir / "devcontainer.json"
            config_file.write_text(
                f'{{\n  "name": "test",\n  "dockerComposeFile": "{workspace}/docker-compose.yml",\n  "service": "app"\n}}'
            )

            # Create docker-compose.yml
            compose_file = workspace / "docker-compose.yml"
            compose_file.write_text("version: '3.8'\nservices:\n  app:\n    build: .")

            result = detect_compose_config(workspace)
            # セキュリティ上の理由で絶対パスは拒否される
            assert result is None

    def test_detect_compose_invalid_json(self):
        """Test detecting compose config with invalid devcontainer.json."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            # Create invalid devcontainer.json
            devcontainer_dir = workspace / ".devcontainer"
            devcontainer_dir.mkdir()
            config_file = devcontainer_dir / "devcontainer.json"
            config_file.write_text("{ invalid json content }")

            result = detect_compose_config(workspace)
            assert result is None
