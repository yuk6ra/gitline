#!/bin/bash

# 環境変数読み込み
source .env.production

# AWSアカウントID取得
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="ap-northeast-1"
FUNCTION_NAME="oracle-ai"

echo "Account ID: $ACCOUNT_ID"
echo "Region: $REGION"

# 1. Lambda実行ロール作成
echo "Creating Lambda execution role..."
aws iam create-role \
  --role-name lambda-github-line-memo-role \
  --assume-role-policy-document file://aws/lambda-trust-policy.json

# Lambda基本実行ポリシーをアタッチ
aws iam attach-role-policy \
  --role-name lambda-github-line-memo-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# 2. ECRリポジトリ作成
echo "Creating ECR repository..."
aws ecr create-repository --repository-name $FUNCTION_NAME --region $REGION

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
  --role arn:aws:iam::$ACCOUNT_ID:role/lambda-github-line-memo-role \
  --timeout 30 \
  --memory-size 512

# 6. 環境変数設定
echo "Setting environment variables..."
aws lambda update-function-configuration \
  --function-name $FUNCTION_NAME \
  --environment "Variables={LINEBOT_CHANNEL_ACCESS_TOKEN=$LINEBOT_CHANNEL_ACCESS_TOKEN,LINEBOT_USER_ID=$LINEBOT_USER_ID,GITHUB_ACCESS_TOKEN=$GITHUB_ACCESS_TOKEN,GITHUB_USERNAME=$GITHUB_USERNAME,GITHUB_REPOSITORY=$GITHUB_REPOSITORY,OPENAI_API_KEY=$OPENAI_API_KEY}"

echo "Lambda function created successfully!"
echo "Function name: $FUNCTION_NAME"
echo "GitHub Secrets設定用:"
echo "  ECR_REPOSITORY: $FUNCTION_NAME"
echo "  LAMBDA_FUNCTION_NAME: $FUNCTION_NAME"
echo "  AWS_REGION: $REGION"