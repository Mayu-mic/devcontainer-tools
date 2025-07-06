"""
CLI メインモジュール

DevContainer管理ツールのコマンドラインインターフェースを提供します。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import click
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .config import create_common_config_template, merge_configurations
from .container import (
    execute_in_container,
    get_container_id,
    get_container_info,
    is_compose_project,
    stop_and_remove_compose_containers,
    stop_and_remove_container,
)
from .utils import find_devcontainer_json, save_json_file

# Richコンソールのインスタンスを作成（カラフルな出力用）
console = Console()


@click.group()
@click.version_option(version=__version__)
def cli() -> None:
    """
    DevContainer簡略化管理ツール

    複雑なdevcontainer CLIオプションを簡略化し、
    設定ファイルの自動マージ機能を提供します。
    """
    pass


@cli.command()
@click.option("--clean", is_flag=True, help="既存のコンテナを削除してから起動")
@click.option("--no-cache", is_flag=True, help="キャッシュを使用せずにビルド")
@click.option(
    "--rebuild", is_flag=True, help="コンテナを再ビルドする（--cleanと--no-cacheを自動的に適用）"
)
@click.option("--gpu", is_flag=True, help="GPU サポートを有効化")
@click.option(
    "--mount", multiple=True, help="追加マウント (形式: source:target または完全なマウント文字列)"
)
@click.option("--env", multiple=True, help="追加環境変数 (形式: NAME=VALUE)")
@click.option(
    "--port", "-p", multiple=True, help="追加ポートフォワード (形式: PORT または PORT:PORT)"
)
@click.option(
    "--workspace",
    type=click.Path(exists=True, path_type=Path),
    default=Path.cwd(),
    help="ワークスペースフォルダ",
)
@click.option(
    "--common-config",
    type=click.Path(path_type=Path),
    default=Path.home() / ".config" / "devcontainer.common.json",
    help="共通設定ファイル",
)
@click.option("--debug", is_flag=True, help="デバッグ情報を表示")
@click.option("--dry-run", is_flag=True, help="設定をマージして表示のみ（実際の起動は行わない）")
@click.option("--auto-forward-ports", is_flag=True, help="forwardPortsをappPortに自動変換する")
def up(
    clean: bool,
    no_cache: bool,
    rebuild: bool,
    gpu: bool,
    mount: tuple[str, ...],
    env: tuple[str, ...],
    port: tuple[str, ...],
    workspace: Path,
    common_config: Path,
    debug: bool,
    dry_run: bool,
    auto_forward_ports: bool,
) -> None:
    """
    開発コンテナを起動または作成する。

    共通設定とプロジェクト設定を自動的にマージします。
    --auto-forward-portsオプションを指定すると、
    forwardPortsからappPortへの変換も行います。
    --rebuildオプションを指定すると、--cleanと--no-cacheが自動的に適用されます。
    """
    # --rebuildフラグが指定された場合、cleanとno_cacheを有効にする
    if rebuild:
        clean = True
        no_cache = True

    console.print("[bold green]Starting devcontainer...[/bold green]")

    # プロジェクト設定を検索
    project_config = find_devcontainer_json(workspace)
    if not project_config:
        console.print("[bold red]✗ devcontainer.json が見つかりません[/bold red]")
        console.print(
            "[yellow]ワークスペースには以下のいずれかが必要です:[/yellow]\n"
            "  • .devcontainer/devcontainer.json\n"
            "  • devcontainer.json"
        )
        sys.exit(1)

    # 環境変数をパース（NAME=VALUE形式）
    env_pairs: list[tuple[str, str]] = []
    for env_var in env:
        if "=" in env_var:
            key, value = env_var.split("=", 1)
            env_pairs.append((key, value))

    # すべての設定をマージ
    merged_config = merge_configurations(
        common_config, project_config, list(mount), env_pairs, list(port), auto_forward_ports
    )

    # dry-runモードの場合は設定表示のみ
    if dry_run:
        console.print("\n[bold blue]🔍 Dry Run Mode - 設定確認のみ[/bold blue]")

        # 設定ファイルの情報を表示
        console.print("\n[bold]設定ソース:[/bold]")
        if project_config:
            console.print(f"📄 プロジェクト設定: {project_config.relative_to(workspace)}")
        else:
            console.print("📄 プロジェクト設定: [yellow]見つかりません[/yellow]")

        if common_config.exists():
            console.print(f"🌐 共通設定: {common_config}")
        else:
            console.print("🌐 共通設定: [yellow]見つかりません[/yellow]")

        if mount or env or port:
            console.print("⚙️  コマンドラインオプション:")
            if mount:
                console.print(f"   マウント: {list(mount)}")
            if env:
                console.print(f"   環境変数: {list(env)}")
            if port:
                console.print(f"   ポート: {list(port)}")

        console.print(
            Panel(JSON(json.dumps(merged_config, indent=2)), title="マージ後の devcontainer.json")
        )
        console.print("\n[green]✅ 設定の確認が完了しました。実際の起動は行いません。[/green]")
        return

    # デバッグモードの場合、マージされた設定を表示
    if debug:
        console.print("\n[bold]Merged configuration:[/bold]")
        console.print(Panel(JSON(json.dumps(merged_config, indent=2)), title="devcontainer.json"))

    # 一時的な設定ファイルを作成
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(merged_config, f, indent=2)
        temp_config_path = f.name

    try:
        # devcontainerコマンドを構築
        cmd = [
            "devcontainer",
            "up",
            "--workspace-folder",
            str(workspace),
            "--override-config",
            temp_config_path,  # マージされた設定を使用
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
@click.argument("command", nargs=-1, required=True)
@click.option(
    "--workspace",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="ワークスペースフォルダ（未指定時は現在のディレクトリを使用）",
)
def exec(command: tuple[str, ...], workspace: Path | None) -> None:
    """
    実行中のコンテナ内でコマンドを実行する。

    コンテナが起動していない場合は、先に 'dev up' を実行してください。
    """
    # コンテナが起動しているかチェック
    from .container import is_container_running

    actual_workspace = workspace or Path.cwd()
    if not is_container_running(actual_workspace):
        console.print("[bold red]❌ コンテナが起動していません。[/bold red]")
        console.print("[yellow]先に 'dev up' を実行してください。[/yellow]")
        sys.exit(1)

    result = execute_in_container(
        workspace=workspace,
        command=list(command),
    )
    sys.exit(result.returncode)


@cli.command()
@click.option("--gpu", is_flag=True, help="GPU サポートを有効化")
@click.option(
    "--mount", multiple=True, help="追加マウント (形式: source:target または完全なマウント文字列)"
)
@click.option("--env", multiple=True, help="追加環境変数 (形式: NAME=VALUE)")
@click.option(
    "--port", "-p", multiple=True, help="追加ポートフォワード (形式: PORT または PORT:PORT)"
)
@click.option(
    "--workspace",
    type=click.Path(exists=True, path_type=Path),
    default=Path.cwd(),
    help="ワークスペースフォルダ",
)
@click.option(
    "--common-config",
    type=click.Path(path_type=Path),
    default=Path.home() / ".config" / "devcontainer.common.json",
    help="共通設定ファイル",
)
@click.option("--debug", is_flag=True, help="デバッグ情報を表示")
@click.option("--dry-run", is_flag=True, help="設定をマージして表示のみ（実際の起動は行わない）")
@click.option("--auto-forward-ports", is_flag=True, help="forwardPortsをappPortに自動変換する")
@click.pass_context
def rebuild(
    ctx: click.Context,
    gpu: bool,
    mount: tuple[str, ...],
    env: tuple[str, ...],
    port: tuple[str, ...],
    workspace: Path,
    common_config: Path,
    debug: bool,
    dry_run: bool,
    auto_forward_ports: bool,
) -> None:
    """
    コンテナを最初から再ビルドする。

    既存のコンテナを削除し、キャッシュを使用せずに
    新しいコンテナをビルドします。

    ⚠️ 非推奨: 代わりに 'dev up --rebuild' を使用してください。
    """
    console.print(
        "[bold yellow]⚠️  警告: 'rebuild' コマンドは非推奨です。代わりに 'dev up --rebuild' を使用してください。[/bold yellow]"
    )
    console.print("[bold yellow]Rebuilding container...[/bold yellow]")

    # upコマンドを--rebuildオプション付きで呼び出す（他のオプションも全て渡す）
    ctx.invoke(
        up,
        clean=False,  # --rebuildで自動的に有効になる
        no_cache=False,  # --rebuildで自動的に有効になる
        rebuild=True,
        gpu=gpu,
        mount=mount,
        env=env,
        port=port,
        workspace=workspace,
        common_config=common_config,
        debug=debug,
        dry_run=dry_run,
        auto_forward_ports=auto_forward_ports,
    )


@cli.command()
@click.option(
    "--workspace",
    type=click.Path(exists=True, path_type=Path),
    default=Path.cwd(),
    help="ワークスペースフォルダ",
)
def status(workspace: Path) -> None:
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
                    mount_list.append(
                        f"• {mount.get('Source', 'Unknown')} → {mount.get('Destination', 'Unknown')}"
                    )
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
        table.add_row("Config", "❌ devcontainerが設定されていません")

    console.print(table)


@cli.command()
@click.option(
    "--workspace",
    type=click.Path(exists=True, path_type=Path),
    default=Path.cwd(),
    help="ワークスペースフォルダ",
)
@click.option("--volumes", is_flag=True, help="関連するボリュームも削除する")
def down(workspace: Path, volumes: bool) -> None:
    """
    開発コンテナを停止・削除する。

    docker-composeプロジェクトの場合はすべてのコンテナを一括停止・削除し、
    単一コンテナの場合は個別に停止・削除します。
    --volumesオプションでボリュームも削除可能です。
    """
    console.print("[bold red]Stopping devcontainer...[/bold red]")

    # docker-composeプロジェクトかどうかを判定
    if is_compose_project(workspace):
        console.print(
            "[cyan]docker-composeプロジェクトを検出しました。すべてのコンテナを停止・削除します。[/cyan]"
        )

        # docker-composeプロジェクトのすべてのコンテナを停止・削除
        success = stop_and_remove_compose_containers(workspace, remove_volumes=volumes)

        if not success:
            console.print(
                "[bold red]✗ docker-composeプロジェクトの停止・削除に失敗しました[/bold red]"
            )
            sys.exit(1)
    else:
        # 単一コンテナの場合
        console.print("[cyan]単一コンテナの停止・削除を実行します。[/cyan]")

        # コンテナが実行中かチェック
        container_id = get_container_id(workspace)

        if not container_id:
            console.print("[yellow]実行中のコンテナが見つかりません。[/yellow]")
            return

        # コンテナを停止・削除
        success = stop_and_remove_container(container_id, remove_volumes=volumes)

        if not success:
            console.print("[bold red]✗ コンテナの停止・削除に失敗しました[/bold red]")
            sys.exit(1)


@cli.command()
@click.option(
    "--common-config",
    type=click.Path(path_type=Path),
    default=Path.home() / ".config" / "devcontainer.common.json",
    help="作成する共通設定ファイル",
)
def init(common_config: Path) -> None:
    """
    共通設定テンプレートを初期化する。

    devcontainer.common.jsonファイルを作成し、
    よく使用される基本的な設定を含めます。
    """
    if common_config.exists():
        console.print(f"[yellow]File {common_config} already exists[/yellow]")
        if not click.confirm("Overwrite?"):
            return

    # 設定ディレクトリが存在しない場合は作成
    common_config.parent.mkdir(parents=True, exist_ok=True)

    # 共通設定のテンプレートを作成
    template = create_common_config_template()

    # ファイルに書き込み
    if save_json_file(template, common_config):
        console.print(f"[green]✓ Created {common_config}[/green]")
    else:
        console.print(f"[red]✗ Failed to create {common_config}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    cli()
