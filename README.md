# GitHub LINE メモ

LINEで送信したメモをGitHubリポジトリに自動保存し、AIによる深堀り質問機能を提供するLINE Botです。

## 機能

- **メモ保存**: LINEで送信したテキストをGitHubリポジトリに自動保存
- **AI深堀り**: OpenAI GPTを使用してメモに関する質問を生成
- **対話セッション**: 質問への回答を通じてメモを深く掘り下げ
- **客観的分析**: AIによるメモの客観的な分析・意見提供
- **セッション管理**: タイムアウト機能付きの対話セッション

## アーキテクチャ

```
LINE Webhook → AWS Lambda → GitHub API
                    ↓
                OpenAI API
```

## セットアップ

### 1. 必要な環境変数

以下の環境変数を設定してください：

```bash
# LINE Bot設定
LINEBOT_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINEBOT_USER_ID=your_line_user_id

# GitHub設定
GITHUB_ACCESS_TOKEN=your_github_personal_access_token
GITHUB_USERNAME=your_github_username
GITHUB_REPOSITORY=your_repository_name

# OpenAI設定
OPENAI_API_KEY=your_openai_api_key
```

### 2. AWS IAMユーザーの作成（GitHub Actions用）

```bash
# IAMユーザーを作成
aws iam create-user --user-name github-actions-lambda-deploy

# ポリシーを作成
aws iam create-policy \
  --policy-name GitHubActionsLambdaDeployPolicy \
  --policy-document file://aws/iam-policy.json

# ポリシーをユーザーにアタッチ
aws iam attach-user-policy \
  --user-name github-actions-lambda-deploy \
  --policy-arn arn:aws:iam::<Account-ID>:policy/GitHubActionsLambdaDeployPolicy

# アクセスキーを作成
aws iam create-access-key --user-name github-actions-lambda-deploy
```

### 3. AWS Lambdaデプロイ

初回セットアップ時は以下のスクリプトを実行：

```bash
# Lambda関数を作成
./create-lambda.sh

# API Gatewayを作成・設定
./create-api-gateway.sh
```

### 4. GitHub Actionsの設定

以下のシークレットをGitHubリポジトリに設定：

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `LINEBOT_CHANNEL_ACCESS_TOKEN`
- `LINEBOT_USER_ID`
- `GITHUB_ACCESS_TOKEN`
- `GITHUB_USERNAME`
- `GITHUB_REPOSITORY`
- `OPENAI_API_KEY`

## 使用方法

### 基本的なメモ保存

1. LINE Botにメッセージを送信
2. 「深堀りしますか？」と聞かれる
3. 「はい」以外を入力すると通常のメモとして保存

### AI深堀りセッション

1. メモ送信後「はい」を入力
2. AIが生成した質問から選択（1-5の番号で回答）
3. 質問に回答
4. 「続けて深堀りしますか？」で継続可能
5. 最大10回まで質問・回答が可能

### 特別なコマンド

- **再考**: 別の角度から質問を再生成
- **終了**: セッションを強制終了
- **AI分析**: AIによる客観的な分析を取得

## 開発

### ローカルテスト

```bash
python app.py
```

環境変数が設定されていない場合はローカルテストモードで動作します。

### ファイル構成

```
├── app.py              # メイン処理（Lambda関数）
├── src/
│   └── note.py         # GitHub API・AI処理
├── aws/
│   ├── iam-policy.json # IAMポリシー
│   └── lambda-trust-policy.json
├── requirements.txt    # Python依存関係
├── Dockerfile         # コンテナ設定
└── create-*.sh        # デプロイスクリプト
```

## デプロイ

プッシュすると自動的にGitHub ActionsによってAWS Lambdaにデプロイされます。

### 手動デプロイ（ECR使用）

```bash
# ECRリポジトリ作成
aws ecr create-repository --repository-name line-git-note-save-note

# Dockerイメージビルド・プッシュ
docker build -t line-git-note-save-note .
docker tag line-git-note-save-note:latest <account-id>.dkr.ecr.ap-northeast-1.amazonaws.com/line-git-note-save-note:latest
docker push <account-id>.dkr.ecr.ap-northeast-1.amazonaws.com/line-git-note-save-note:latest
```

## トラブルシューティング

### 502 Bad Gateway

Lambda関数が適切なHTTPレスポンス（statusCode: 200）を返していることを確認してください。

### メモが保存されない

- GitHub Personal Access Tokenの権限を確認
- リポジトリ名とユーザー名が正しいことを確認

### AI機能が動作しない

- OpenAI API Keyが有効であることを確認
- API使用量制限に達していないか確認
