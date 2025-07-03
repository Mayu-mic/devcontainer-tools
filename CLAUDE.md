# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

DevContainer Toolsは、複雑なdevcontainer CLIを簡略化し、チーム開発向けの設定マージ機能を提供するPythonパッケージです。日本語でコメントされており、uvによる依存関係管理を採用しています。

## 開発環境セットアップ

### 初回セットアップ
```bash
# ワンコマンドでセットアップ
make setup
```

### 従来のコマンド（必要に応じて）
```bash
# 依存関係のインストール
uv sync --dev

# パッケージのローカルインストール（CLI利用のため）
# 開発中は --editable を使用して変更を即座に反映
uv tool install --editable .
```

## 開発用コマンド

### 品質チェック
```bash
# 全品質チェック（CI環境と同じ）
make check

# 個別チェック
make lint           # ruff linting
make format         # ruff formatting
make type-check     # mypy type checking
make test           # pytest testing
```

### Pre-commit Hooks
```bash
# 自動実行（git commit時）
git commit -m "your message"

# 手動実行
make pre-commit-run

# 全ファイルでチェック
uv run pre-commit run --all-files
```

### テスト実行
```bash
# 基本テスト実行
make test

# カバレッジ付きテスト
make test-cov

# 特定のテストファイル
uv run pytest tests/test_config.py

# 特定のテストメソッド
uv run pytest tests/test_config.py::TestDeepMerge::test_simple_merge
```

### 旧コマンド（直接実行）
```bash
# Linting
uv run ruff check .
uv run ruff check --fix .

# フォーマット
uv run ruff format .
uv run ruff format --check .

# 型チェック
uv run mypy src/
```

### パッケージビルド
```bash
# パッケージビルド
uv build

# 開発モードでの再インストール
uv tool uninstall devcontainer-tools
uv tool install --editable .
```

## 使用例

### 基本的な使用方法
```bash
# 通常の起動（forwardPortsは変換されない）
dev up

# 設定確認のみ
dev up --dry-run

# コンテナを再ビルド（--cleanと--no-cacheを自動適用）
dev up --rebuild

# 再ビルドと追加オプションを組み合わせ
dev up --rebuild --port 3000 --mount /host:/container --env NODE_ENV=development

# forwardPortsをappPortに自動変換して起動
dev up --auto-forward-ports

# 追加オプションと組み合わせ
dev up --auto-forward-ports --mount /host:/container --env NODE_ENV=development
```

### forwardPorts自動変換について

**デフォルト動作（推奨）:**
```bash
dev up  # forwardPortsはそのまま保持、appPortには変換されない
```

**従来の動作（必要時のみ）:**
```bash
dev up --auto-forward-ports  # forwardPortsがappPortに変換される
```

この変更により：
- VS Code拡張機能は`forwardPorts`を正常に認識
- devcontainer CLIは`appPort`を使用（`--auto-forward-ports`指定時のみ）
- 設定の重複や競合を回避

### コマンド体系の改善

**新しいコマンド体系（推奨）:**
```bash
# 基本起動
dev up

# リビルド付き起動（--cleanと--no-cacheを自動適用）
dev up --rebuild

# オプションと組み合わせ可能
dev up --rebuild --port 3000:3000 --mount ./data:/app/data --env NODE_ENV=dev
```

**従来のコマンド（後方互換性のために維持）:**
```bash
# 非推奨警告が表示されるが、機能は維持
dev rebuild

# 全オプションが利用可能
dev rebuild --port 3000 --mount /host:/container --env NODE_ENV=development
```

## アーキテクチャ

### モジュール構成

- **cli.py**: Click使用のCLIエントリーポイント。すべてのサブコマンド（up, exec, status, rebuild, init）を定義
- **config.py**: 設定マージのコアロジック。deep_merge関数とmerge_configurations関数が中心
- **container.py**: Docker操作（コンテナID取得、docker exec実行）
- **utils.py**: 汎用ユーティリティ（JSON読み書き、devcontainer.json検索）

### 設定マージの仕組み

優先順位: **コマンドラインオプション > プロジェクト設定 > 共通設定**

1. `devcontainer.common.json`（チーム共通設定）を読み込み
2. `.devcontainer/devcontainer.json`（プロジェクト設定）を読み込み
3. `--auto-forward-ports`オプション指定時のみ`forwardPorts` → `appPort` 自動変換を実行
4. コマンドライン引数（--mount, --env, --port）を追加
5. 一時ファイルとして保存し、`devcontainer up --override-config`で使用

### CLIコマンドの処理フロー

- **up**: 設定マージ → 一時ファイル作成 → devcontainer CLIに委譲
  - `--dry-run`オプションで設定確認のみ可能
  - `--auto-forward-ports`オプションで`forwardPorts`から`appPort`への自動変換を有効化
  - `--rebuild`オプションで`--clean`と`--no-cache`を自動適用
- **exec**: コンテナID検出 → docker exec優先、フォールバックでdevcontainer exec
- **status**: コンテナID取得 → docker inspectで詳細情報表示
- **rebuild**: 非推奨警告表示 → 内部的に`dev up --rebuild`を呼び出し（全オプション対応）

## テスト戦略

- **単体テスト**: 各モジュールの関数レベル
- **CLIテスト**: click.testing.CliRunnerを使用
- **モック**: subprocess.runやDocker操作をモック
- **テンポラリファイル**: tempfile使用で安全なファイル操作テスト

## 重要な実装詳細

### 設定ファイル検索順序
1. `.devcontainer/devcontainer.json`
2. `devcontainer.json`（ルート）

### マウント文字列パース
- 簡略形式: `/host:/container` → 完全形式: `source=/host,target=/container,type=bind,consistency=cached`

### Rich Console出力
全てのユーザー向け出力はrichライブラリを使用。色付き、テーブル表示対応。

### JSONC（コメント付きJSON）サポート
`devcontainer.json`のコメント（`//`）をサポートするため、`json5`ライブラリを使用してパースを実行。

## コーディングスタイル

### 型アノテーション
- **Union型**: `Optional[X]`ではなく`X | None`を使用してください
- **Future import**: 各ファイルの先頭に`from __future__ import annotations`を追加してください
- Python 3.9+互換性を保ちながら、モダンな型構文を使用します

### 例
```python
from __future__ import annotations

from pathlib import Path

def example_function(path: Path | None) -> str | None:
    """型アノテーションの例"""
    if path is None:
        return None
    return str(path)
```

## 日本語対応

コメント、ドキュメント、CLI ヘルプはすべて日本語です。新しい機能追加時も日本語でのコメントとヘルプテキストを維持してください。
