"""
コンテナ操作モジュール

Dockerコンテナの操作に関する機能を提供します。
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, cast

from rich.console import Console

console = Console()


def _truncate_output(output: str, max_length: int = 200) -> str:
    """
    長い出力を切り詰めて表示用に整形する。

    Args:
        output: 元の出力文字列
        max_length: 最大文字数

    Returns:
        切り詰められた文字列
    """
    if len(output) > max_length:
        return f"{output[:max_length]}..."
    return output


def _get_error_message(result: subprocess.CompletedProcess[str]) -> str:
    """
    プロセス実行結果からエラーメッセージを構築する。

    優先順位: stderr → stdout → 終了コード

    Args:
        result: subprocess.CompletedProcessオブジェクト

    Returns:
        エラーメッセージ文字列
    """
    if result.stderr:
        return result.stderr.strip()
    elif result.stdout:
        return result.stdout.strip()
    else:
        return f"プロセス終了コード: {result.returncode}"


def run_command(
    cmd: list[str],
    check: bool = True,
    capture_output: bool = True,
    text: bool = True,
    verbose: bool = False,
) -> subprocess.CompletedProcess[str]:
    """
    コマンドを実行し、結果を返す。

    Args:
        cmd: 実行するコマンドのリスト
        check: エラー時に例外を発生させるかどうか
        capture_output: 出力をキャプチャするかどうか
        text: テキストモードで実行するかどうか
        verbose: 詳細なデバッグ情報を表示するかどうか

    Returns:
        コマンドの実行結果
    """
    console.print(f"[cyan]実行中:[/cyan] {' '.join(cmd)}")
    result = subprocess.run(cmd, check=check, capture_output=capture_output, text=text)

    if verbose:
        console.print(f"[dim]デバッグ情報: returncode={result.returncode}[/dim]")
        if result.stdout:
            console.print(f"[dim]stdout: {_truncate_output(result.stdout)}[/dim]")
        if result.stderr:
            console.print(f"[dim]stderr: {_truncate_output(result.stderr)}[/dim]")

    return result


def get_container_id(workspace: Path) -> str | None:
    """
    現在のワークスペースに対応するコンテナIDを取得する。

    docker-composeプロジェクトの場合は専用の取得メソッドを使用し、
    そうでない場合はDockerのラベルを使用してコンテナを検索する。

    Args:
        workspace: ワークスペースのパス

    Returns:
        コンテナID（見つからない場合はNone）
    """
    try:
        # docker-composeプロジェクトの場合は専用の取得メソッドを使用
        if is_compose_project(workspace):
            return get_compose_container_id(workspace)

        # 通常のコンテナの場合はラベルで検索
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


def get_container_info(container_id: str) -> dict[str, Any] | None:
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
        result = run_command(cmd, check=False, verbose=True)

        if result.returncode == 0:
            console.print("[bold green]✓ コンテナの自動起動が完了しました[/bold green]")
            return True
        else:
            error_msg = _get_error_message(result)
            console.print(f"[bold red]✗ コンテナの起動に失敗しました: {error_msg}[/bold red]")
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
        result = run_command(["docker", "stop", container_id], check=False, verbose=True)

        if result.returncode != 0:
            error_msg = _get_error_message(result)
            console.print(f"[red]コンテナの停止に失敗しました: {error_msg}[/red]")
            return False

        # コンテナを削除
        console.print("[yellow]コンテナを削除しています...[/yellow]")
        cmd = ["docker", "rm", container_id]
        if remove_volumes:
            cmd.append("-v")  # ボリュームも削除

        result = run_command(cmd, check=False, verbose=True)

        if result.returncode != 0:
            error_msg = _get_error_message(result)
            console.print(f"[red]コンテナの削除に失敗しました: {error_msg}[/red]")
            return False

        console.print("[green]✓ コンテナの停止・削除が完了しました[/green]")
        return True

    except Exception as e:
        console.print(f"[red]コンテナの停止・削除中にエラーが発生しました: {e}[/red]")
        return False


def execute_in_container(
    workspace: Path | None,
    command: list[str],
) -> subprocess.CompletedProcess[str]:
    """
    コンテナ内でコマンドを実行する（devcontainer CLI使用）

    Args:
        workspace: ワークスペースのパス（Noneの場合は現在のディレクトリを使用）
        command: 実行するコマンド

    Returns:
        コマンドの実行結果
    """
    # devcontainer execでは常にデフォルトの"."を使用
    workspace_folder = "."

    cmd = [
        "devcontainer",
        "exec",
        "--workspace-folder",
        workspace_folder,
    ] + command
    return subprocess.run(cmd, text=True)


def is_compose_project(workspace: Path) -> bool:
    """
    ワークスペースがdocker-composeプロジェクトかどうかを判定する。

    Args:
        workspace: ワークスペースのパス

    Returns:
        docker-composeプロジェクトの場合True、そうでない場合False
    """
    from .utils import detect_compose_config

    compose_config = detect_compose_config(workspace)
    return compose_config is not None


def get_compose_containers(workspace: Path) -> list[str]:
    """
    docker-composeプロジェクトのコンテナ一覧を取得する。

    Args:
        workspace: ワークスペースのパス

    Returns:
        コンテナIDのリスト
    """
    try:
        from .utils import detect_compose_config

        # compose設定を取得
        compose_config = detect_compose_config(workspace)
        if not compose_config:
            return []

        compose_file = compose_config["compose_file"]

        # -f オプションでcompose ファイルを明示指定してコンテナ一覧を取得
        result = run_command(
            ["docker", "compose", "-f", str(compose_file), "ps", "-q"],
            check=False,
        )

        if result.returncode == 0 and result.stdout and result.stdout.strip():
            return [
                container_id.strip()
                for container_id in result.stdout.strip().split("\n")
                if container_id.strip()
            ]

        return []
    except Exception:
        return []


def stop_and_remove_compose_containers(workspace: Path, remove_volumes: bool = False) -> bool:
    """
    docker-composeプロジェクトのすべてのコンテナを停止・削除する。

    Args:
        workspace: ワークスペースのパス
        remove_volumes: 関連するボリュームも削除するかどうか

    Returns:
        成功した場合True、失敗した場合False
    """
    try:
        from .utils import detect_compose_config

        # compose設定を取得
        compose_config = detect_compose_config(workspace)
        if not compose_config:
            console.print("[red]docker-compose設定が見つかりません[/red]")
            return False

        compose_file = compose_config["compose_file"]
        console.print("[yellow]docker-composeプロジェクトを停止・削除しています...[/yellow]")

        # -f オプションでcompose ファイルを明示指定
        cmd = ["docker", "compose", "-f", str(compose_file), "down"]
        if remove_volumes:
            cmd.append("-v")  # ボリュームも削除

        result = run_command(cmd, check=False, verbose=True)

        if result.returncode != 0:
            error_msg = _get_error_message(result)
            console.print(
                f"[red]docker-composeプロジェクトの停止・削除に失敗しました: {error_msg}[/red]"
            )
            return False

        console.print("[green]✓ docker-composeプロジェクトの停止・削除が完了しました[/green]")
        return True

    except Exception as e:
        console.print(
            f"[red]docker-composeプロジェクトの停止・削除中にエラーが発生しました: {e}[/red]"
        )
        return False


def get_compose_container_id(workspace: Path, service_name: str | None = None) -> str | None:
    """
    docker-composeプロジェクトから指定されたサービスのコンテナIDを取得する。

    Args:
        workspace: ワークスペースのパス
        service_name: サービス名（省略時は最初のサービス）

    Returns:
        コンテナID（見つからない場合はNone）
    """
    try:
        from .utils import detect_compose_config

        # compose設定を確認
        compose_config = detect_compose_config(workspace)
        if not compose_config:
            return None

        # service_nameが指定されていない場合は、devcontainer.jsonから取得
        if not service_name:
            service_name = compose_config["devcontainer_config"].get("service")
            if not service_name:
                # サービス名が不明な場合は最初のコンテナを取得
                containers = get_compose_containers(workspace)
                return containers[0] if containers else None

        # 指定されたサービスのコンテナIDを取得
        compose_file = compose_config["compose_file"]
        result = run_command(
            ["docker", "compose", "-f", str(compose_file), "ps", "-q", service_name],
            check=False,
        )

        if result.returncode == 0 and result.stdout and result.stdout.strip():
            return result.stdout.strip().split("\n")[0]

    except Exception:
        pass

    return None
