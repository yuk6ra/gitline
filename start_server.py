#!/usr/bin/env python3
"""
Oracle AI Web Server Launcher
ローカル開発用のサーバー起動スクリプト
"""

import os
import sys
import uvicorn
from pathlib import Path

import dotenv

dotenv.load_dotenv()

def main():
    # 環境変数の確認
    print("=== Oracle AI Web Server ===")
    print("環境変数チェック中...")
    
    required_vars = ["GITHUB_ACCESS_TOKEN", "GITHUB_USERNAME", "GITHUB_REPOSITORY", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ 必要な環境変数が設定されていません: {missing_vars}")
        print("\n設定方法:")
        print("export GITHUB_ACCESS_TOKEN=your_token")
        print("export GITHUB_USERNAME=your_username")
        print("export GITHUB_REPOSITORY=your_repository")
        print("export OPENAI_API_KEY=your_openai_key")
        print("\nまたは .env ファイルを作成してください")
        sys.exit(1)
    
    print("✅ 環境変数OK")
    print(f"GitHub Repository: {os.environ['GITHUB_USERNAME']}/{os.environ['GITHUB_REPOSITORY']}")
    print("🚀 サーバー起動中...")
    
    # FastAPIサーバー起動
    uvicorn.run(
        "web_app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 開発モード
        log_level="info"
    )

if __name__ == "__main__":
    main()