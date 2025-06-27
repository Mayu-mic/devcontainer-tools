# DevContainer Tools

シンプルで強力なDevContainer管理ツール - 複雑な設定を簡単に、チーム開発を効率的に。

## ✨ 特徴

- 🚀 **簡略化されたコマンド**: 複雑なdevcontainer CLIオプションを直感的なインターフェースに
- 🔄 **自動設定マージ**: 共通設定とプロジェクト設定を自動的に統合
- 🎯 **forwardPorts変換**: VS CodeのforwardPortsを自動的にappPortに変換
- 👥 **チーム対応**: 共通設定を共有して一貫した開発環境を提供
- 💻 **高速実行**: 可能な場合はdocker execを直接使用してパフォーマンス向上
- 🎨 **リッチな出力**: カラフルで読みやすいコンソール出力

## 📦 インストール

### 前提条件

devcontainer CLIが必要です。インストールされていない場合は以下を実行してください：

```bash
npm install -g @devcontainers/cli
```

### uvツールとしてインストール（推奨）

```bash
# GitHubから直接インストール
uv tool install --from git+https://github.com/Mayu-mic/devcontainer-tools --name dev

# ローカルディレクトリからインストール
cd devcontainer-tools
uv tool install --editable .
```

### 開発者向けインストール

```bash
git clone https://github.com/Mayu-mic/devcontainer-tools
cd devcontainer-tools

# ワンコマンドでセットアップ
make setup
```

### 開発用コマンド

```bash
# 全品質チェック実行
make check

# 個別コマンド
make test           # テスト実行
make lint           # リント実行
make format         # フォーマット
make type-check     # 型チェック

# Pre-commit手動実行
make pre-commit-run
```

## 🚀 使い方

### 初期セットアップ

```bash
# 共通設定ファイルを作成
dev init
```

これにより `devcontainer.common.json` が作成され、チーム共通の基本設定が含まれます。

### 基本的な使用方法

```bash
# 基本的なコンテナ起動
dev up

# GPU サポート付きで起動
dev up --gpu

# 既存コンテナを削除してクリーンビルド
dev up --clean --no-cache

# 追加マウントとポートフォワードを指定
dev up --mount /host/data:/workspace/data --port 8080

# 環境変数を追加
dev up --env NODE_ENV=development --env DEBUG=true

# デバッグモードで設定内容を確認
dev up --debug

# 設定をマージして確認のみ（実際の起動は行わない）
dev up --dry-run
```

### コンテナ操作

```bash
# コンテナ内でコマンド実行
dev exec bash
dev exec npm install
dev exec python manage.py runserver

# コンテナの状態確認
dev status

# コンテナの完全再ビルド
dev rebuild
```

## ⚙️ 設定ファイル

### プロジェクト構造

```
your-project/
├── .devcontainer/
│   └── devcontainer.json      # プロジェクト固有の設定
├── devcontainer.common.json   # チーム共通設定（オプション）
└── ... (その他のファイル)
```

### 設定の優先順位

1. **コマンドラインオプション** (最優先)
2. **プロジェクト設定** (`.devcontainer/devcontainer.json`)
3. **共通設定** (`devcontainer.common.json`)

### 共通設定の例 (`devcontainer.common.json`)

```json
{
  "features": {
    "ghcr.io/anthropics/devcontainer-features/claude-code:latest": {},
    "ghcr.io/devcontainers/features/node:1": {
      "version": "lts"
    }
  },
  "mounts": [
    "source=${env:HOME}/.claude,target=/home/vscode/.claude,type=bind,consistency=cached",
    "source=${env:HOME}/.ssh,target=/home/vscode/.ssh,type=bind,consistency=cached"
  ],
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-vscode.vscode-typescript-next"
      ]
    }
  }
}
```

### プロジェクト設定の例 (`.devcontainer/devcontainer.json`)

```json
{
  "name": "My Project",
  "image": "mcr.microsoft.com/devcontainers/python:3.11",
  "forwardPorts": [8000, 5432],
  "postCreateCommand": "pip install -r requirements.txt",
  "remoteEnv": {
    "PYTHONPATH": "/workspace"
  }
}
```

## 🔄 自動変換機能

### forwardPorts → appPort

プロジェクト設定で `forwardPorts` を指定すると、自動的に `appPort` として扱われます：

```json
// 入力
{
  "forwardPorts": [8000, 3000]
}

// 自動変換後
{
  "forwardPorts": [8000, 3000],
  "appPort": [8000, 3000]
}
```

### マウント形式の変換

簡略形式のマウント指定が自動的に完全形式に変換されます：

```bash
# 簡略形式
dev up --mount /host/path:/container/path

# 自動変換後
# \"source=/host/path,target=/container/path,type=bind,consistency=cached\"
```

## 🛠️ 開発

### 要件

- Python 3.8+
- uv
- Docker
- devcontainer CLI

devcontainer CLIのインストール:
```bash
npm install -g @devcontainers/cli
```

### 開発セットアップ

```bash
# リポジトリをクローン
git clone https://github.com/Mayu-mic/devcontainer-tools
cd devcontainer-tools

# 依存関係をインストール
uv sync --dev

# 開発中の変更を即座に反映させるためにeditableモードでインストール
uv tool install --editable .

# テストを実行
uv run pytest

# コードフォーマット
uv run ruff check --fix .
uv run ruff format .

# 型チェック
uv run mypy src/
```

### テスト

```bash
# 全テストを実行（カバレッジ付き）
uv run pytest

# 特定のテストを実行
uv run pytest tests/test_config.py

# カバレッジなしでテスト実行
uv run pytest --no-cov
```

## 📚 コマンドリファレンス

### `dev up`

開発コンテナを起動または作成します。

```bash
dev up [OPTIONS]
```

**オプション:**
- `--clean`: 既存のコンテナを削除してから起動
- `--no-cache`: キャッシュを使用せずにビルド
- `--gpu`: GPU サポートを有効化
- `--mount TEXT`: 追加マウント（複数指定可）
- `--env TEXT`: 追加環境変数（複数指定可）
- `--port TEXT`: 追加ポートフォワード（複数指定可）
- `--workspace PATH`: ワークスペースフォルダ（デフォルト: カレントディレクトリ）
- `--common-config PATH`: 共通設定ファイル（デフォルト: devcontainer.common.json）
- `--debug`: デバッグ情報を表示
- `--dry-run`: 設定をマージして表示のみ（実際の起動は行わない）

### `dev exec`

実行中のコンテナ内でコマンドを実行します。

```bash
dev exec [OPTIONS] COMMAND...
```

**オプション:**
- `--workspace PATH`: ワークスペースフォルダ
- `--no-up`: コンテナが起動していない場合でも自動起動しない

### `dev status`

コンテナのステータスと設定を表示します。

```bash
dev status [OPTIONS]
```

**オプション:**
- `--workspace PATH`: ワークスペースフォルダ

### `dev rebuild`

コンテナを最初から再ビルドします。

```bash
dev rebuild [OPTIONS]
```

**オプション:**
- `--workspace PATH`: ワークスペースフォルダ

### `dev init`

共通設定テンプレートを初期化します。

```bash
dev init [OPTIONS]
```

**オプション:**
- `--common-config PATH`: 作成する共通設定ファイル

## 🔧 トラブルシューティング

### よくある問題

**Q: `devcontainer: command not found` エラーが出る**
A: devcontainer CLIがインストールされていません。以下でインストールしてください：
```bash
npm install -g @devcontainers/cli
```

**Q: コンテナが見つからない**
A: `dev status` でコンテナの状態を確認し、必要に応じて `dev up` で起動してください。

**Q: 設定がマージされない**
A: `dev up --debug` でマージされた設定を確認し、ファイルパスが正しいかチェックしてください。

### ログ出力

詳細なログが必要な場合は、デバッグモードを使用してください：

```bash
dev up --debug
```

## 🤝 貢献

プロジェクトへの貢献を歓迎します！

1. リポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は [LICENSE](LICENSE) ファイルを参照してください。

## 🙏 謝辞

- [devcontainers/cli](https://github.com/devcontainers/cli) - 基盤となるdevcontainer CLI
- [click](https://click.palletsprojects.com/) - 優れたCLIフレームワーク
- [rich](https://rich.readthedocs.io/) - 美しいコンソール出力
