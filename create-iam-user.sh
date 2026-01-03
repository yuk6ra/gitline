#!/bin/bash
set -e

USER_NAME="github-actions-lambda-deploy"

echo "Creating IAM user: $USER_NAME"

# ユーザー作成（既に存在する場合はスキップ）
if aws iam get-user --user-name $USER_NAME &> /dev/null; then
  echo "User $USER_NAME already exists, skipping..."
else
  aws iam create-user --user-name $USER_NAME
fi

# マネージドポリシーをアタッチ
echo "Attaching managed policies..."
aws iam attach-user-policy \
  --user-name $USER_NAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser

aws iam attach-user-policy \
  --user-name $USER_NAME \
  --policy-arn arn:aws:iam::aws:policy/AWSLambda_FullAccess

# アクセスキー作成
echo "Creating access key..."
aws iam create-access-key --user-name $USER_NAME

echo ""
echo "=========================================="
echo "IAM user created successfully!"
echo "=========================================="
echo ""
echo "Set the above credentials as GitHub Secrets:"
echo "  AWS_ACCESS_KEY_ID"
echo "  AWS_SECRET_ACCESS_KEY"
echo "  AWS_REGION (e.g., ap-northeast-1)"
