# Makefile
.PHONY: help setup install test lint format type-check clean check pre-commit-install pre-commit-run

# デフォルトターゲット
help:
	@echo "利用可能なコマンド:"
	@echo "  make setup          - 開発環境の初期セットアップ"
	@echo "  make install        - 依存関係のインストール"
	@echo "  make test           - テスト実行"
	@echo "  make lint           - リント実行"
	@echo "  make format         - コードフォーマット"
	@echo "  make type-check     - 型チェック"
	@echo "  make check          - CI環境と同じチェックを実行"
	@echo "  make pre-commit-run - pre-commit手動実行"
	@echo "  make clean          - キャッシュファイル削除"

# 開発環境セットアップ（メインコマンド）
setup: install pre-commit-install
	@echo "✅ 開発環境のセットアップが完了しました"
	@echo "📝 git commit時に自動的にpre-commitが実行されます"

# 依存関係インストール
install:
	@echo "📦 依存関係をインストール中..."
	uv sync --dev
	uv pip install -e .[dev]

# Pre-commit hooks インストール
pre-commit-install:
	@echo "🔧 Pre-commit hooksをインストール中..."
	uv run pre-commit install
	@echo "🧪 全ファイルでpre-commitテスト実行中..."
	uv run pre-commit run --all-files || true

# テスト実行
test:
	@echo "🧪 テスト実行中..."
	uv run pytest

# テスト（カバレッジ付き）
test-cov:
	@echo "🧪 カバレッジ付きテスト実行中..."
	uv run pytest --cov=devcontainer_tools --cov-report=term --cov-report=html

# リント実行
lint:
	@echo "🔍 リント実行中..."
	uv run ruff check .

# リント修正
lint-fix:
	@echo "🔧 リント自動修正中..."
	uv run ruff check --fix .

# フォーマット確認
format-check:
	@echo "📏 フォーマット確認中..."
	uv run black --check .

# フォーマット実行
format:
	@echo "📏 フォーマット実行中..."
	uv run black .

# 型チェック
type-check:
	@echo "🔍 型チェック実行中..."
	uv run mypy src/

# CI環境と同じチェック
check: lint format-check type-check test
	@echo "✅ すべてのチェックが完了しました"

# Pre-commit手動実行
pre-commit-run:
	@echo "🔧 Pre-commit手動実行中..."
	uv run pre-commit run --all-files

# キャッシュクリア
clean:
	@echo "🗑️  キャッシュファイル削除中..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ coverage.xml .coverage 2>/dev/null || true
