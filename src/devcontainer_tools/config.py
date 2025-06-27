"""
設定管理モジュール

devcontainer.jsonの設定をマージ・管理する機能を提供します。
"""

import json
from pathlib import Path
from typing import Any, Optional

from .utils import find_devcontainer_json, load_json_file, parse_mount_string


def deep_merge(target: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    """
    2つの辞書を深くマージする。

    ネストされた辞書は再帰的にマージされ、
    リストは結合されて重複が削除される。

    Args:
        target: マージ先の辞書
        source: マージ元の辞書

    Returns:
        マージされた辞書
    """
    result = target.copy()

    for key, value in source.items():
        if key in result:
            # 両方が辞書の場合は再帰的にマージ
            if isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = deep_merge(result[key], value)
            # 両方がリストの場合は結合して重複を削除
            elif isinstance(result[key], list) and isinstance(value, list):
                combined = result[key] + value
                # JSON形式で文字列化できる単純な値の場合は重複を削除
                try:
                    # JSONで文字列化してからセットで重複を削除し、再度パース
                    unique_items = list(dict.fromkeys(map(json.dumps, combined)).keys())
                    result[key] = [json.loads(item) for item in unique_items]
                except (TypeError, json.JSONDecodeError):
                    # JSON化できない場合は単純に結合
                    result[key] = combined
            else:
                # その他の場合は上書き
                result[key] = value
        else:
            # キーが存在しない場合は追加
            result[key] = value

    return result


def merge_configurations(
    common_config_path: Optional[Path],
    project_config_path: Optional[Path],
    additional_mounts: list[str],
    additional_env: list[tuple[str, str]],
    additional_ports: list[str],
) -> dict[str, Any]:
    """
    すべての設定をマージする。

    マージ順序（優先度順）:
    1. コマンドラインオプション（最優先）
    2. プロジェクト設定（.devcontainer/devcontainer.json）（ベース）
    3. 共通設定（devcontainer.common.json）（補完のみ）

    プロジェクト設定をベースとし、共通設定で不足部分のみを補完する。
    プロジェクト設定が存在する項目は共通設定で上書きされない。

    ポート設定の処理:
    - forwardPorts: VS Code用設定（読み取り専用として保持）
    - appPort: devcontainer CLI用設定（forwardPorts + 追加ポート）
    
    Note: devcontainer CLIはforwardPortsを認識しないため、
          appPortに変換して追加ポートと組み合わせる。
          forwardPortsは元の値のまま保持され、VS Code連携用に残される。

    特殊な処理:
    - forwardPortsをappPortに自動変換
    - マウント、環境変数、ポートの追加

    Args:
        common_config_path: 共通設定ファイルのパス
        project_config_path: プロジェクト設定ファイルのパス
        additional_mounts: 追加マウントのリスト
        additional_env: 追加環境変数のリスト（タプル）
        additional_ports: 追加ポートのリスト

    Returns:
        マージされた設定辞書
    """
    # プロジェクト設定をベースとして開始
    if project_config_path and project_config_path.exists():
        project_config = load_json_file(project_config_path)

        # forwardPorts -> appPort の自動変換
        # devcontainer CLIはforwardPortsを認識しないため、appPortに変換
        # forwardPortsは読み取り専用として保持し、VS Code連携用に残す
        if "forwardPorts" in project_config:
            project_config["appPort"] = project_config["forwardPorts"].copy()

        merged = project_config.copy()
    else:
        merged = {}

    # 共通設定で不足部分を補完（プロジェクト設定を優先）
    if common_config_path and common_config_path.exists():
        common_config = load_json_file(common_config_path)
        # 共通設定をベースに、プロジェクト設定で上書き
        merged = deep_merge(common_config, merged)

    # コマンドラインから追加マウントを設定
    if additional_mounts:
        if "mounts" not in merged:
            merged["mounts"] = []
        for mount in additional_mounts:
            parsed_mount = parse_mount_string(mount)
            # 重複を避けるため、既存のマウントリストにない場合のみ追加
            if parsed_mount not in merged["mounts"]:
                merged["mounts"].append(parsed_mount)

    # コマンドラインから追加環境変数を設定
    if additional_env:
        if "remoteEnv" not in merged:
            merged["remoteEnv"] = {}
        for key, value in additional_env:
            merged["remoteEnv"][key] = value

    # コマンドラインから追加ポートを設定
    if additional_ports:
        if "appPort" not in merged:
            merged["appPort"] = []
        elif not isinstance(merged["appPort"], list):
            # appPortが単一の値の場合はリストに変換
            merged["appPort"] = [merged["appPort"]]

        # ポートをそのまま追加（パースなし）
        for port in additional_ports:
            if port not in merged["appPort"]:
                merged["appPort"].append(port)

    return merged


def create_common_config_template() -> dict[str, Any]:
    """
    共通設定テンプレートを作成する。

    Returns:
        共通設定のテンプレート辞書
    """
    return {
        "features": {
            # Claude Codeのサポートを追加
            "ghcr.io/anthropics/devcontainer-features/claude-code:latest": {}
        },
        "mounts": [
            # Claude設定ディレクトリをマウント
            "source=${env:HOME}${env:USERPROFILE}/.claude,target=/home/vscode/.claude,type=bind,consistency=cached"
        ],
        "customizations": {
            "vscode": {
                "extensions": [
                    # ここに共通で使用する拡張機能を追加
                ]
            }
        },
    }


def get_workspace_folder(workspace: Path) -> str:
    """
    devcontainer.jsonからworkspaceFolderを取得する。

    devcontainer.jsonにworkspaceFolderが定義されていない場合は、
    デフォルト値として'/workspace'を返す。

    Args:
        workspace: ワークスペースのパス

    Returns:
        workspaceFolder値（デフォルト: /workspace）
    """
    # devcontainer.jsonを検索
    config_path = find_devcontainer_json(workspace)
    if not config_path:
        return "/workspace"

    # 設定ファイルを読み込み
    config = load_json_file(config_path)

    # workspaceFolderを取得（未定義の場合はデフォルト値）
    workspace_folder = config.get("workspaceFolder", "/workspace")
    if isinstance(workspace_folder, str):
        return workspace_folder
    return "/workspace"
