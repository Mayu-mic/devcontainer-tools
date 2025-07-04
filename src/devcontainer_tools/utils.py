"""
ユーティリティ関数

共通で使用される汎用的な関数を提供します。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import json5
from rich.console import Console

console = Console()


def load_json_file(file_path: Path) -> dict[str, Any]:
    """
    JSONまたはJSONCファイルを安全に読み込む。

    devcontainer.jsonのようなコメント付きJSONもサポートします。
    エラーが発生した場合は警告を表示し、空の辞書を返す。

    Args:
        file_path: 読み込むJSONファイルのパス

    Returns:
        パースされたJSON（辞書）、エラーの場合は空の辞書
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
        # 空ファイルの場合は空の辞書を返す
        if not content.strip():
            return {}
        # json5でコメント付きJSONをパース
        return cast(dict[str, Any], json5.loads(content))
    except FileNotFoundError:
        console.print(f"[yellow]Warning: File not found: {file_path}[/yellow]")
        return {}
    except ValueError as e:
        console.print(f"[yellow]Warning: Invalid JSON in {file_path}: {e}[/yellow]")
        return {}
    except Exception as e:
        console.print(f"[yellow]Warning: Could not load {file_path}: {e}[/yellow]")
        return {}


def find_devcontainer_json(workspace: Path) -> Path | None:
    """
    ワークスペース内のdevcontainer.jsonファイルを検索する。

    以下の順序で検索:
    1. .devcontainer/devcontainer.json
    2. devcontainer.json (ルート)

    Args:
        workspace: 検索するワークスペースのパス

    Returns:
        見つかったdevcontainer.jsonのパス、見つからない場合はNone
    """
    candidates = [
        workspace / ".devcontainer" / "devcontainer.json",
        workspace / "devcontainer.json",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


def parse_mount_string(mount_str: str) -> str:
    """
    マウント文字列を解析し、devcontainer形式に変換する。

    サポートする形式:
    - source=path,target=path,type=bind,consistency=cached (完全形式)
    - /host/path:/container/path (簡略形式)

    Args:
        mount_str: マウント文字列

    Returns:
        devcontainer形式のマウント文字列
    """
    # すでに正しい形式の場合はそのまま返す
    if "source=" in mount_str and "target=" in mount_str:
        return mount_str

    # source:target形式の場合は変換
    parts = mount_str.split(":")
    if len(parts) == 2:
        return f"source={parts[0]},target={parts[1]},type=bind,consistency=cached"

    # その他の場合はそのまま返す
    return mount_str


def save_json_file(data: dict[str, Any], file_path: Path, indent: int = 2) -> bool:
    """
    辞書をJSONファイルとして保存する。

    Args:
        data: 保存するデータ
        file_path: 保存先のファイルパス
        indent: インデントレベル

    Returns:
        保存に成功した場合True、失敗した場合False
    """
    try:
        # ディレクトリが存在しない場合は作成
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        return True
    except Exception as e:
        console.print(f"[red]Error: Could not save {file_path}: {e}[/red]")
        return False


def detect_compose_config(workspace: Path) -> dict[str, Any] | None:
    """
    docker-compose設定を検出する。

    devcontainer.jsonからdockerComposeFileを検索し、
    対応するdocker-compose.ymlファイルの存在を確認する。

    Args:
        workspace: ワークスペースのパス

    Returns:
        compose設定の辞書（compose_fileとdevcontainer_configを含む）、
        見つからない場合はNone
    """
    try:
        # devcontainer.jsonを検索
        devcontainer_path = find_devcontainer_json(workspace)
        if not devcontainer_path:
            return None

        # devcontainer.jsonを読み込み
        config = load_json_file(devcontainer_path)
        if not config:
            return None

        # dockerComposeFileの設定をチェック
        docker_compose_file = config.get("dockerComposeFile")
        if not docker_compose_file:
            return None

        # dockerComposeFileが配列の場合は最初の要素を使用
        if isinstance(docker_compose_file, list):
            if not docker_compose_file:
                return None
            docker_compose_file = docker_compose_file[0]

        # セキュリティチェック: 絶対パスは拒否
        if Path(docker_compose_file).is_absolute():
            console.print(
                f"[yellow]Warning: Absolute path in dockerComposeFile is not allowed: {docker_compose_file}[/yellow]"
            )
            return None

        # devcontainer.jsonからの相対パスでcompose ファイルを解決
        devcontainer_dir = devcontainer_path.parent
        compose_file_path = (devcontainer_dir / docker_compose_file).resolve()

        # セキュリティチェック: ワークスペース外のファイルは拒否
        try:
            compose_file_path.relative_to(workspace.resolve())
        except ValueError:
            console.print(
                f"[yellow]Warning: Compose file outside workspace is not allowed: {compose_file_path}[/yellow]"
            )
            return None

        # compose ファイルの存在確認
        if not compose_file_path.exists():
            return None

        return {
            "compose_file": compose_file_path,
            "devcontainer_config": config,
        }
    except Exception as e:
        console.print(f"[yellow]Warning: Could not detect compose config: {e}[/yellow]")
        return None


def get_compose_project_name(workspace: Path, compose_config: dict[str, Any] | None = None) -> str:
    """
    docker-composeプロジェクト名を取得する。

    Args:
        workspace: ワークスペースのパス
        compose_config: compose設定（detect_compose_configの結果）

    Returns:
        プロジェクト名（通常はディレクトリ名）
    """
    if compose_config and "devcontainer_config" in compose_config:
        # devcontainer.jsonにプロジェクト名が指定されている場合
        project_name = compose_config["devcontainer_config"].get("name")
        if project_name:
            # プロジェクト名を正規化（docker-composeの命名規則に従う）
            import re

            return re.sub(r"[^a-z0-9_-]", "", project_name.lower())

    # デフォルトはワークスペースのディレクトリ名
    return workspace.name.lower()
