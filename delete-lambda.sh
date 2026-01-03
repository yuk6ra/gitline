#!/bin/bash
set -e

# 引数チェック
if [ -z "$1" ]; then
  echo "Usage: $0 <function-name>"
  echo "Example: $0 oracle-ai"
  exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="ap-northeast-1"
FUNCTION_NAME="$1"
ROLE_NAME="${FUNCTION_NAME}-role"

echo "Account ID: $ACCOUNT_ID"
echo "Region: $REGION"
echo "Function Name: $FUNCTION_NAME"
echo "Role Name: $ROLE_NAME"
echo ""

# 確認
read -p "Are you sure you want to delete Lambda '$FUNCTION_NAME' and related resources? (y/N): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
  echo "Cancelled."
  exit 0
fi

# 1. Lambda関数削除
echo "Deleting Lambda function..."
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION &> /dev/null; then
  aws lambda delete-function --function-name $FUNCTION_NAME --region $REGION
  echo "Lambda function deleted."
else
  echo "Lambda function not found, skipping..."
fi

# 2. ECRリポジトリ削除（イメージも含めて強制削除）
echo "Deleting ECR repository..."
if aws ecr describe-repositories --repository-names $FUNCTION_NAME --region $REGION &> /dev/null; then
  aws ecr delete-repository --repository-name $FUNCTION_NAME --region $REGION --force
  echo "ECR repository deleted."
else
  echo "ECR repository not found, skipping..."
fi

# 3. IAMロール削除（ポリシーをデタッチしてから削除）
echo "Deleting IAM role..."
if aws iam get-role --role-name $ROLE_NAME &> /dev/null; then
  # アタッチされたポリシーをデタッチ
  POLICIES=$(aws iam list-attached-role-policies --role-name $ROLE_NAME --query 'AttachedPolicies[].PolicyArn' --output text)
  for policy in $POLICIES; do
    echo "Detaching policy: $policy"
    aws iam detach-role-policy --role-name $ROLE_NAME --policy-arn $policy
  done

  aws iam delete-role --role-name $ROLE_NAME
  echo "IAM role deleted."
else
  echo "IAM role not found, skipping..."
fi

echo ""
echo "=========================================="
echo "Lambda resources deleted successfully!"
echo "=========================================="
echo "Deleted: $FUNCTION_NAME"
