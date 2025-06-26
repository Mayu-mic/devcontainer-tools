"""
ユーティリティ関数

共通で使用される汎用的な関数を提供します。
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

from rich.console import Console

console = Console()


def load_json_file(file_path: Path) -> Dict[str, Any]:
    """
    JSONファイルを安全に読み込む。
    
    エラーが発生した場合は警告を表示し、空の辞書を返す。
    
    Args:
        file_path: 読み込むJSONファイルのパス
    
    Returns:
        パースされたJSON（辞書）、エラーの場合は空の辞書
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        console.print(f"[yellow]Warning: File not found: {file_path}[/yellow]")
        return {}
    except json.JSONDecodeError as e:
        console.print(f"[yellow]Warning: Invalid JSON in {file_path}: {e}[/yellow]")
        return {}
    except Exception as e:
        console.print(f"[yellow]Warning: Could not load {file_path}: {e}[/yellow]")
        return {}


def find_devcontainer_json(workspace: Path) -> Optional[Path]:
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
        workspace / "devcontainer.json"
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
    parts = mount_str.split(':')
    if len(parts) == 2:
        return f"source={parts[0]},target={parts[1]},type=bind,consistency=cached"
    
    # その他の場合はそのまま返す
    return mount_str


def save_json_file(data: Dict[str, Any], file_path: Path, indent: int = 2) -> bool:
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
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        return True
    except Exception as e:
        console.print(f"[red]Error: Could not save {file_path}: {e}[/red]")
        return False