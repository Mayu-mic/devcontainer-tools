"""Tests for configuration management module."""

import json
import tempfile
from pathlib import Path

from devcontainer_tools.config import (
    create_common_config_template,
    deep_merge,
    merge_configurations,
)


class TestDeepMerge:
    """Test the deep_merge function."""

    def test_simple_merge(self):
        """Test merging simple dictionaries."""
        target = {"a": 1, "b": 2}
        source = {"b": 3, "c": 4}
        result = deep_merge(target, source)

        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_dict_merge(self):
        """Test merging nested dictionaries."""
        target = {"features": {"node": {"version": "16"}}}
        source = {"features": {"python": {"version": "3.9"}}}
        result = deep_merge(target, source)

        expected = {"features": {"node": {"version": "16"}, "python": {"version": "3.9"}}}
        assert result == expected

    def test_list_merge(self):
        """Test merging lists with duplicate removal."""
        target = {"ports": [8000, 3000]}
        source = {"ports": [3000, 9000]}
        result = deep_merge(target, source)

        # Should contain all unique ports
        assert set(result["ports"]) == {8000, 3000, 9000}

    def test_list_merge_complex(self):
        """Test merging lists with complex objects."""
        target = {"mounts": ["source=/host1,target=/container1"]}
        source = {"mounts": ["source=/host2,target=/container2"]}
        result = deep_merge(target, source)

        assert len(result["mounts"]) == 2
        assert "source=/host1,target=/container1" in result["mounts"]
        assert "source=/host2,target=/container2" in result["mounts"]

    def test_override_primitive(self):
        """Test that primitive values are overridden."""
        target = {"name": "old"}
        source = {"name": "new"}
        result = deep_merge(target, source)

        assert result["name"] == "new"


class TestMergeConfigurations:
    """Test the merge_configurations function."""

    def test_merge_with_no_configs(self):
        """Test merging with no configuration files."""
        result = merge_configurations(None, None, [], [], [])
        assert result == {}

    def test_merge_with_common_config_only(self):
        """Test merging with only common configuration."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            common_config = {"features": {"claude-code": {}}}
            json.dump(common_config, f)
            common_path = Path(f.name)

        try:
            result = merge_configurations(common_path, None, [], [], [])
            assert result["features"]["claude-code"] == {}
        finally:
            common_path.unlink()

    def test_forward_ports_conversion_disabled_by_default(self):
        """Test that forwardPorts to appPort conversion is disabled by default."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            project_config = {"forwardPorts": [8000, 3000]}
            json.dump(project_config, f)
            project_path = Path(f.name)

        try:
            result = merge_configurations(None, project_path, [], [], [], auto_forward_ports=False)
            assert result["forwardPorts"] == [8000, 3000]
            assert "appPort" not in result
        finally:
            project_path.unlink()

    def test_forward_ports_conversion_enabled(self):
        """Test that forwardPorts to appPort conversion works when enabled."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            project_config = {"forwardPorts": [8000, 3000]}
            json.dump(project_config, f)
            project_path = Path(f.name)

        try:
            result = merge_configurations(None, project_path, [], [], [], auto_forward_ports=True)
            assert result["forwardPorts"] == [8000, 3000]
            assert result["appPort"] == [8000, 3000]
        finally:
            project_path.unlink()

    def test_forward_ports_conversion_legacy(self):
        """Test backward compatibility - old function signature still works."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            project_config = {"forwardPorts": [8000, 3000]}
            json.dump(project_config, f)
            project_path = Path(f.name)

        try:
            # 古い関数署名でもテストが通るか確認（互換性のため）
            result = merge_configurations(None, project_path, [], [], [])
            assert result["forwardPorts"] == [8000, 3000]
            # デフォルトでは変換されない
            assert "appPort" not in result
        finally:
            project_path.unlink()

    def test_additional_mounts(self):
        """Test adding additional mounts."""
        additional_mounts = ["/host:/container"]
        result = merge_configurations(None, None, additional_mounts, [], [])

        assert "mounts" in result
        assert "source=/host,target=/container,type=bind,consistency=cached" in result["mounts"]

    def test_additional_env_vars(self):
        """Test adding additional environment variables."""
        additional_env = [("NODE_ENV", "development"), ("DEBUG", "true")]
        result = merge_configurations(None, None, [], additional_env, [])

        assert result["remoteEnv"]["NODE_ENV"] == "development"
        assert result["remoteEnv"]["DEBUG"] == "true"

    def test_additional_ports(self):
        """Test adding additional ports."""
        additional_ports = ["8080", "9000"]
        result = merge_configurations(None, None, [], [], additional_ports)

        assert result["appPort"] == ["8080", "9000"]

    def test_full_merge_scenario(self):
        """Test a complete merge scenario with all types of configurations."""
        # Create common config
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            common_config = {
                "features": {"claude-code": {}},
                "mounts": ["source=/common,target=/common"],
            }
            json.dump(common_config, f)
            common_path = Path(f.name)

        # Create project config
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            project_config = {
                "name": "test-project",
                "forwardPorts": [8000],
                "features": {"python": {"version": "3.9"}},
            }
            json.dump(project_config, f)
            project_path = Path(f.name)

        try:
            # auto_forward_ports=Trueでテスト
            result = merge_configurations(
                common_path,
                project_path,
                ["/additional:/mount"],
                [("TEST_VAR", "test_value")],
                ["9000"],
                auto_forward_ports=True,
            )

            # Check that all configurations are merged
            assert result["name"] == "test-project"
            assert result["forwardPorts"] == [
                8000
            ]  # Original only (not modified by additional ports)
            assert result["appPort"] == [8000, "9000"]  # Converted from forwardPorts + additional
            assert "claude-code" in result["features"]
            assert "python" in result["features"]
            assert len(result["mounts"]) == 2  # common + additional
            assert result["remoteEnv"]["TEST_VAR"] == "test_value"

        finally:
            common_path.unlink()
            project_path.unlink()


class TestCreateCommonConfigTemplate:
    """Test the create_common_config_template function."""

    def test_template_structure(self):
        """Test that the template has the expected structure."""
        template = create_common_config_template()

        assert "features" in template
        assert "mounts" in template
        assert "customizations" in template

        # Check for Claude Code feature
        assert "ghcr.io/anthropics/devcontainer-features/claude-code:latest" in template["features"]

        # Check for Claude mount
        claude_mount = "source=${env:HOME}${env:USERPROFILE}/.claude,target=/home/vscode/.claude,type=bind,consistency=cached"
        assert claude_mount in template["mounts"]

        # Check VSCode customizations
        assert "vscode" in template["customizations"]
        assert "extensions" in template["customizations"]["vscode"]
