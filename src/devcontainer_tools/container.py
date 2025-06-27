"""
コンテナ操作モジュール

Dockerコンテナの操作に関する機能を提供します。
"""

import json
import subprocess
from pathlib import Path
from typing import Any, Optional, cast

from rich.console import Console

from .config import InvalidWorkspaceFolderError, get_workspace_folder, sanitize_workspace_folder

console = Console()


def run_command(
    cmd: list[str], check: bool = True, capture_output: bool = True, text: bool = True
) -> subprocess.CompletedProcess[str]:
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
        result = run_command(
            ["docker", "ps", "-q", "-f", f"label=devcontainer.local_folder={workspace}"],
            check=False,
        )

        if result.returncode == 0 and result.stdout and result.stdout.strip():
            return result.stdout.strip().split("\n")[0]

        # 代替のラベル形式で検索（VS Code形式）
        result = run_command(
            ["docker", "ps", "-q", "-f", f"label=vscode.devcontainer.id={workspace.name}"],
            check=False,
        )

        if result.returncode == 0 and result.stdout and result.stdout.strip():
            return result.stdout.strip().split("\n")[0]

    except Exception:
        pass

    return None


def get_container_info(container_id: str) -> Optional[dict[str, Any]]:
    """
    コンテナの詳細情報を取得する。

    Args:
        container_id: コンテナID

    Returns:
        コンテナ情報の辞書、取得できない場合はNone
    """
    try:
        result = run_command(["docker", "inspect", container_id], check=False)
        if result.returncode == 0 and result.stdout:
            info_list = json.loads(result.stdout)
            if info_list:
                return cast(dict[str, Any], info_list[0])
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


def ensure_container_running(workspace: Path) -> bool:
    """
    コンテナが実行されていることを確認し、必要に応じて起動する。

    Args:
        workspace: ワークスペースのパス

    Returns:
        コンテナが利用可能な場合True、そうでない場合False
    """
    if is_container_running(workspace):
        return True

    console.print("[yellow]コンテナが起動していません。自動的に起動しています...[/yellow]")

    try:
        # devcontainer upを実行
        cmd = ["devcontainer", "up", "--workspace-folder", str(workspace)]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            console.print("[bold green]✓ コンテナの自動起動が完了しました[/bold green]")
            return True
        else:
            console.print(f"[bold red]✗ コンテナの起動に失敗しました: {result.stderr}[/bold red]")
            return False
    except Exception as e:
        console.print(f"[bold red]✗ コンテナの起動中にエラーが発生しました: {e}[/bold red]")
        return False


def stop_and_remove_container(container_id: str, remove_volumes: bool = False) -> bool:
    """
    コンテナを停止し、削除する。

    Args:
        container_id: 停止・削除するコンテナのID
        remove_volumes: 関連するボリュームも削除するかどうか

    Returns:
        成功した場合True、失敗した場合False
    """
    try:
        # コンテナを停止
        console.print(f"[yellow]コンテナを停止しています... (ID: {container_id[:12]})[/yellow]")
        result = run_command(["docker", "stop", container_id], check=False)

        if result.returncode != 0:
            console.print(f"[red]コンテナの停止に失敗しました: {result.stderr}[/red]")
            return False

        # コンテナを削除
        console.print("[yellow]コンテナを削除しています...[/yellow]")
        cmd = ["docker", "rm", container_id]
        if remove_volumes:
            cmd.append("-v")  # ボリュームも削除

        result = run_command(cmd, check=False)

        if result.returncode != 0:
            console.print(f"[red]コンテナの削除に失敗しました: {result.stderr}[/red]")
            return False

        console.print("[green]✓ コンテナの停止・削除が完了しました[/green]")
        return True

    except Exception as e:
        console.print(f"[red]コンテナの停止・削除中にエラーが発生しました: {e}[/red]")
        return False


def execute_in_container(
    workspace: Path,
    command: list[str],
    use_docker_exec: bool = True,
    auto_up: bool = False,
    workspace_folder: Optional[str] = None,
) -> subprocess.CompletedProcess[str]:
    """
    コンテナ内でコマンドを実行する。

    Args:
        workspace: ワークスペースのパス
        command: 実行するコマンド
        use_docker_exec: docker execを使用するかどうか
        auto_up: コンテナが起動していない場合に自動起動するかどうか
        workspace_folder: ワーキングディレクトリ（Noneの場合は自動取得）

    Returns:
        コマンドの実行結果
    """
    # workspace_folderが指定されていない場合は自動取得
    if workspace_folder is None:
        workspace_folder = get_workspace_folder(workspace)
    else:
        # 明示的に指定されたworkspace_folderもサニタイズ
        try:
            workspace_folder = sanitize_workspace_folder(workspace_folder)
        except InvalidWorkspaceFolderError:
            # 無効なパスの場合はエラーを再発生
            raise

    if use_docker_exec:
        container_id = get_container_id(workspace)
        if container_id:
            # docker execを直接使用（高速）
            # -wオプションでワーキングディレクトリを指定
            cmd = ["docker", "exec", "-it", "-w", workspace_folder, container_id] + command
            return subprocess.run(cmd, text=True)
        elif auto_up:
            # 自動起動を試行
            if ensure_container_running(workspace):
                # 再度コンテナIDを取得
                container_id = get_container_id(workspace)
                if container_id:
                    cmd = ["docker", "exec", "-it", "-w", workspace_folder, container_id] + command
                    return subprocess.run(cmd, text=True)

    # devcontainer execを使用（フォールバック）
    cmd = ["devcontainer", "exec", "--workspace-folder", str(workspace)] + command
    return subprocess.run(cmd, text=True)
