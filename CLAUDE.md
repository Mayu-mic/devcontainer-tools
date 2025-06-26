# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

DevContainer Toolsは、複雑なdevcontainer CLIを簡略化し、チーム開発向けの設定マージ機能を提供するPythonパッケージです。日本語でコメントされており、uvによる依存関係管理を採用しています。

## 開発環境セットアップ

```bash
# 依存関係のインストール
uv sync --dev
uv pip install -e .[dev]

# パッケージのローカルインストール（CLI利用のため）
uv tool install --from . --name dev
```

## 開発用コマンド

### テスト実行
```bash
# 全テスト実行
uv run pytest

# カバレッジ付きテスト
uv run pytest --cov=devcontainer_tools

# 特定のテストファイル
uv run pytest tests/test_config.py

# 特定のテストメソッド
uv run pytest tests/test_config.py::TestDeepMerge::test_simple_merge
```

### コード品質チェック
```bash
# Linting
uv run ruff check .
uv run ruff check --fix .

# フォーマット
uv run black .
uv run black --check .

# 型チェック
uv run mypy src/
```

### パッケージビルド
```bash
# パッケージビルド
uv build

# 開発モードでの再インストール
uv tool uninstall dev
uv tool install --from . --name dev
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
3. `forwardPorts` → `appPort` 自動変換を実行
4. コマンドライン引数（--mount, --env, --port）を追加
5. 一時ファイルとして保存し、`devcontainer up --override-config`で使用

### CLIコマンドの処理フロー

- **up**: 設定マージ → 一時ファイル作成 → devcontainer CLIに委譲
- **exec**: コンテナID検出 → docker exec優先、フォールバックでdevcontainer exec
- **status**: コンテナID取得 → docker inspectで詳細情報表示

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

## 日本語対応

コメント、ドキュメント、CLI ヘルプはすべて日本語です。新しい機能追加時も日本語でのコメントとヘルプテキストを維持してください。