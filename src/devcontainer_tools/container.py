"""
コンテナ操作モジュール

Dockerコンテナの操作に関する機能を提供します。
"""

import json
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any

from rich.console import Console

console = Console()


def run_command(
    cmd: List[str], 
    check: bool = True,
    capture_output: bool = True,
    text: bool = True
) -> subprocess.CompletedProcess:
    """
    コマンドを実行し、結果を返す。
    
    Args:
        cmd: 実行するコマンドのリスト
        check: エラー時に例外を発生させるかどうか
        capture_output: 出力をキャプチャするかどうか
        text: テキストモードで実行するかどうか
    
    Returns:
        コマンドの実行結果
    """
    console.print(f"[cyan]Executing:[/cyan] {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, capture_output=capture_output, text=text)


def get_container_id(workspace: Path) -> Optional[str]:
    """
    現在のワークスペースに対応するコンテナIDを取得する。
    
    Dockerのラベルを使用してコンテナを検索する。
    複数のラベル形式を試す。
    
    Args:
        workspace: ワークスペースのパス
    
    Returns:
        コンテナID（見つからない場合はNone）
    """
    try:
        # ワークスペースフォルダのラベルで検索
        result = run_command([
            "docker", "ps", "-q", "-f",
            f"label=devcontainer.local_folder={workspace}"
        ], check=False)
        
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split('\n')[0]
        
        # 代替のラベル形式で検索（VS Code形式）
        result = run_command([
            "docker", "ps", "-q", "-f",
            f"label=vscode.devcontainer.id={workspace.name}"
        ], check=False)
        
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split('\n')[0]
        
    except Exception:
        pass
    
    return None


def get_container_info(container_id: str) -> Optional[Dict[str, Any]]:
    """
    コンテナの詳細情報を取得する。
    
    Args:
        container_id: コンテナID
    
    Returns:
        コンテナ情報の辞書、取得できない場合はNone
    """
    try:
        result = run_command(["docker", "inspect", container_id], check=False)
        if result.returncode == 0:
            info_list = json.loads(result.stdout)
            if info_list:
                return info_list[0]
    except (json.JSONDecodeError, IndexError):
        pass
    
    return None


def is_container_running(workspace: Path) -> bool:
    """
    ワークスペースのコンテナが実行中かどうかを確認する。
    
    Args:
        workspace: ワークスペースのパス
    
    Returns:
        実行中の場合True、そうでない場合False
    """
    return get_container_id(workspace) is not None


def execute_in_container(
    workspace: Path,
    command: List[str],
    use_docker_exec: bool = True
) -> subprocess.CompletedProcess:
    """
    コンテナ内でコマンドを実行する。
    
    Args:
        workspace: ワークスペースのパス
        command: 実行するコマンド
        use_docker_exec: docker execを使用するかどうか
    
    Returns:
        コマンドの実行結果
    """
    if use_docker_exec:
        container_id = get_container_id(workspace)
        if container_id:
            # docker execを直接使用（高速）
            cmd = ["docker", "exec", "-it", container_id] + command
            return subprocess.run(cmd)
    
    # devcontainer execを使用（フォールバック）
    cmd = [
        "devcontainer", "exec",
        "--workspace-folder", str(workspace)
    ] + command
    return subprocess.run(cmd)