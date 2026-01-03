#!/bin/bash
set -e  # エラー時に停止

# 引数チェック
if [ -z "$1" ]; then
  echo "Usage: $0 <function-name>"
  echo "Example: $0 oracle-ai"
  exit 1
fi

# Dockerが使えるかチェック
if ! command -v docker &> /dev/null; then
  echo "Error: Docker is not available."
  echo "Please start Docker Desktop and enable WSL2 integration."
  exit 1
fi

# 環境変数読み込み
source .env.production

# AWSアカウントID取得
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="ap-northeast-1"
FUNCTION_NAME="$1"
ROLE_NAME="${FUNCTION_NAME}-role"

echo "Account ID: $ACCOUNT_ID"
echo "Region: $REGION"
echo "Function Name: $FUNCTION_NAME"
echo "Role Name: $ROLE_NAME"

# 1. Lambda実行ロール作成（既に存在する場合はスキップ）
echo "Creating Lambda execution role..."
if aws iam get-role --role-name $ROLE_NAME &> /dev/null; then
  echo "Role $ROLE_NAME already exists, skipping..."
else
  aws iam create-role \
    --role-name $ROLE_NAME \
    --assume-role-policy-document file://aws/lambda-trust-policy.json

  # Lambda基本実行ポリシーをアタッチ
  aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
fi

# 2. ECRリポジトリ作成（既に存在する場合はスキップ）
echo "Creating ECR repository..."
if aws ecr describe-repositories --repository-names $FUNCTION_NAME --region $REGION &> /dev/null; then
  echo "ECR repository $FUNCTION_NAME already exists, skipping..."
else
  aws ecr create-repository --repository-name $FUNCTION_NAME --region $REGION
fi

# 3. ECRにログイン
echo "Logging into ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# 4. Dockerイメージビルド・プッシュ
echo "Building and pushing Docker image..."
docker build -t $FUNCTION_NAME .
docker tag $FUNCTION_NAME:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$FUNCTION_NAME:latest
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$FUNCTION_NAME:latest

# 5. Lambda関数作成（少し待ってからロールが有効になるように）
echo "Waiting for IAM role to be available..."
sleep 10

echo "Creating Lambda function..."
aws lambda create-function \
  --function-name $FUNCTION_NAME \
  --package-type Image \
  --code ImageUri=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$FUNCTION_NAME:latest \
  --role arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME \
  --timeout 30 \
  --memory-size 512

# 6. Lambda更新待ち
echo "Waiting for Lambda function to be ready..."
aws lambda wait function-active --function-name $FUNCTION_NAME

# 7. 環境変数設定（JSON形式で安全に渡す）
echo "Setting environment variables..."
ENV_JSON=$(cat <<EOF
{
  "Variables": {
    "LINEBOT_CHANNEL_ACCESS_TOKEN": "${LINEBOT_CHANNEL_ACCESS_TOKEN}",
    "LINEBOT_USER_ID": "${LINEBOT_USER_ID}",
    "GITHUB_ACCESS_TOKEN": "${GITHUB_ACCESS_TOKEN}",
    "GITHUB_USERNAME": "${GITHUB_USERNAME}",
    "GITHUB_REPOSITORY": "${GITHUB_REPOSITORY}",
    "OPENAI_API_KEY": "${OPENAI_API_KEY:-}"
  }
}
EOF
)

aws lambda update-function-configuration \
  --function-name $FUNCTION_NAME \
  --environment "$ENV_JSON"

echo ""
echo "=========================================="
echo "Lambda function created successfully!"
echo "=========================================="
echo "Function name: $FUNCTION_NAME"
echo "Role name: $ROLE_NAME"
echo ""
echo "GitHub Secrets設定用:"
echo "  ECR_REPOSITORY: $FUNCTION_NAME"
echo "  LAMBDA_FUNCTION_NAME: $FUNCTION_NAME"
echo "  AWS_REGION: $REGION"