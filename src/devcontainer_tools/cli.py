"""
CLI メインモジュール

DevContainer管理ツールのコマンドラインインターフェースを提供します。
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple

import click
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .config import create_common_config_template, merge_configurations
from .container import execute_in_container, get_container_id, get_container_info
from .utils import find_devcontainer_json, save_json_file

# Richコンソールのインスタンスを作成（カラフルな出力用）
console = Console()


@click.group()
@click.version_option(version=__version__)
def cli():
    """
    DevContainer簡略化管理ツール
    
    複雑なdevcontainer CLIオプションを簡略化し、
    設定ファイルの自動マージ機能を提供します。
    """
    pass


@cli.command()
@click.option('--clean', is_flag=True, help='既存のコンテナを削除してから起動')
@click.option('--no-cache', is_flag=True, help='キャッシュを使用せずにビルド')
@click.option('--gpu', is_flag=True, help='GPU サポートを有効化')
@click.option('--mount', multiple=True, help='追加マウント (形式: source:target または完全なマウント文字列)')
@click.option('--env', multiple=True, help='追加環境変数 (形式: NAME=VALUE)')
@click.option('--port', multiple=True, help='追加ポートフォワード (形式: PORT または PORT:PORT)')
@click.option('--workspace', type=click.Path(exists=True, path_type=Path), default=Path.cwd(), help='ワークスペースフォルダ')
@click.option('--common-config', type=click.Path(path_type=Path), default=Path('devcontainer.common.json'), help='共通設定ファイル')
@click.option('--debug', is_flag=True, help='デバッグ情報を表示')
def up(clean, no_cache, gpu, mount, env, port, workspace, common_config, debug):
    """
    開発コンテナを起動または作成する。
    
    共通設定とプロジェクト設定を自動的にマージし、
    forwardPortsからappPortへの変換も行います。
    """
    console.print("[bold green]Starting devcontainer...[/bold green]")

    # プロジェクト設定を検索
    project_config = find_devcontainer_json(workspace)
    if not project_config:
        console.print("[yellow]No devcontainer.json found in workspace[/yellow]")

    # 環境変数をパース（NAME=VALUE形式）
    env_pairs: List[Tuple[str, str]] = []
    for env_var in env:
        if '=' in env_var:
            key, value = env_var.split('=', 1)
            env_pairs.append((key, value))

    # すべての設定をマージ
    merged_config = merge_configurations(
        common_config,
        project_config,
        list(mount),
        env_pairs,
        list(port)
    )

    # デバッグモードの場合、マージされた設定を表示
    if debug:
        console.print("\n[bold]Merged configuration:[/bold]")
        console.print(Panel(JSON(json.dumps(merged_config, indent=2)), title="devcontainer.json"))

    # 一時的な設定ファイルを作成
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(merged_config, f, indent=2)
        temp_config_path = f.name

    try:
        # devcontainerコマンドを構築
        cmd = [
            "devcontainer", "up",
            "--workspace-folder", str(workspace),
            "--override-config", temp_config_path  # マージされた設定を使用
        ]

        # オプションフラグを追加
        if clean:
            cmd.append("--remove-existing-container")

        if no_cache:
            cmd.append("--build-no-cache")

        if gpu:
            cmd.extend(["--gpu-availability", "all"])

        # コマンドを実行（対話的なため出力をキャプチャしない）
        result = subprocess.run(cmd)

        if result.returncode == 0:
            console.print("[bold green]✓ Container started successfully![/bold green]")
        else:
            console.print("[bold red]✗ Failed to start container[/bold red]")
            sys.exit(result.returncode)

    finally:
        # 一時ファイルをクリーンアップ
        os.unlink(temp_config_path)


@cli.command()
@click.argument('command', nargs=-1, required=True)
@click.option('--workspace', type=click.Path(exists=True, path_type=Path), default=Path.cwd(), help='ワークスペースフォルダ')
@click.option('--no-up', is_flag=True, help='コンテナが起動していない場合でも自動起動しない')
def exec(command, workspace, no_up):
    """
    実行中のコンテナ内でコマンドを実行する。
    
    可能な場合はdocker execを直接使用してパフォーマンスを向上させる。
    コンテナが見つからない場合、デフォルトで自動的にコンテナを起動する。
    --no-upオプションを指定すると従来通りエラーで停止する。
    """
    result = execute_in_container(workspace, list(command), auto_up=not no_up)
    sys.exit(result.returncode)


@cli.command()
@click.option('--workspace', type=click.Path(exists=True, path_type=Path), default=Path.cwd(), help='ワークスペースフォルダ')
@click.pass_context
def rebuild(ctx, workspace):
    """
    コンテナを最初から再ビルドする。
    
    既存のコンテナを削除し、キャッシュを使用せずに
    新しいコンテナをビルドします。
    """
    console.print("[bold yellow]Rebuilding container...[/bold yellow]")
    # upコマンドを--cleanと--no-cacheオプション付きで呼び出す
    ctx.invoke(up, clean=True, no_cache=True, workspace=workspace)


@cli.command()
@click.option('--workspace', type=click.Path(exists=True, path_type=Path), default=Path.cwd(), help='ワークスペースフォルダ')
def status(workspace):
    """
    コンテナのステータスと設定を表示する。
    
    実行中のコンテナの情報、マウント状況、
    使用中の設定ファイルなどを表示します。
    """
    console.print("[bold]DevContainer Status[/bold]\n")

    # コンテナが実行中かチェック
    container_id = get_container_id(workspace)

    # 情報テーブルを作成
    table = Table(title="Container Information")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Workspace", str(workspace))

    if container_id:
        table.add_row("Status", "✓ Running")
        table.add_row("Container ID", container_id[:12])

        # コンテナの詳細情報を取得
        info = get_container_info(container_id)
        if info:
            table.add_row("Image", info.get("Config", {}).get("Image", "Unknown"))

            # マウント情報を表示（最初の3つ）
            mounts = info.get("Mounts", [])
            if mounts:
                mount_list = []
                for mount in mounts[:3]:
                    mount_list.append(f"• {mount.get('Source', 'Unknown')} → {mount.get('Destination', 'Unknown')}")
                if len(mounts) > 3:
                    mount_list.append(f"• ... and {len(mounts) - 3} more")
                table.add_row("Mounts", "\n".join(mount_list))
    else:
        table.add_row("Status", "✗ Not running")

    # 設定ファイルの確認
    config_path = find_devcontainer_json(workspace)
    if config_path:
        table.add_row("Config", str(config_path.relative_to(workspace)))
    else:
        table.add_row("Config", "Not found")

    console.print(table)


@cli.command()
@click.option('--common-config', type=click.Path(path_type=Path), default=Path('devcontainer.common.json'), help='作成する共通設定ファイル')
def init(common_config):
    """
    共通設定テンプレートを初期化する。
    
    devcontainer.common.jsonファイルを作成し、
    よく使用される基本的な設定を含めます。
    """
    if common_config.exists():
        console.print(f"[yellow]File {common_config} already exists[/yellow]")
        if not click.confirm("Overwrite?"):
            return

    # 共通設定のテンプレートを作成
    template = create_common_config_template()

    # ファイルに書き込み
    if save_json_file(template, common_config):
        console.print(f"[green]✓ Created {common_config}[/green]")
    else:
        console.print(f"[red]✗ Failed to create {common_config}[/red]")
        sys.exit(1)


if __name__ == '__main__':
    cli()
