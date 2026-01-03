#!/bin/bash
set -e

# 引数チェック
if [ -z "$1" ]; then
  echo "Usage: $0 <api-name or api-id>"
  echo "Example: $0 oracle-ai-api"
  echo "Example: $0 abc123def4"
  exit 1
fi

REGION="ap-northeast-1"
INPUT="$1"

# API IDを取得（名前で検索、または直接IDとして使用）
echo "Searching for API..."
API_ID=$(aws apigateway get-rest-apis --region $REGION --query "items[?name=='$INPUT'].id" --output text)

if [ -z "$API_ID" ]; then
  # 名前で見つからない場合、入力をIDとして扱う
  if aws apigateway get-rest-api --rest-api-id $INPUT --region $REGION &> /dev/null; then
    API_ID=$INPUT
  else
    echo "Error: API not found with name or ID: $INPUT"
    echo ""
    echo "Available APIs:"
    aws apigateway get-rest-apis --region $REGION --query 'items[].{ID:id,Name:name}' --output table
    exit 1
  fi
fi

API_NAME=$(aws apigateway get-rest-api --rest-api-id $API_ID --region $REGION --query 'name' --output text)

echo "Found API:"
echo "  ID: $API_ID"
echo "  Name: $API_NAME"
echo ""

# 確認
read -p "Are you sure you want to delete this API Gateway? (y/N): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
  echo "Cancelled."
  exit 0
fi

# API Gateway削除（リトライ付き）
echo "Deleting API Gateway..."
MAX_RETRIES=5
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  if aws apigateway delete-rest-api --rest-api-id $API_ID --region $REGION 2>&1; then
    echo ""
    echo "=========================================="
    echo "API Gateway deleted successfully!"
    echo "=========================================="
    echo "Deleted: $API_NAME ($API_ID)"
    exit 0
  else
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
      echo "Rate limited. Waiting 30 seconds before retry ($RETRY_COUNT/$MAX_RETRIES)..."
      sleep 30
    fi
  fi
done

echo "Error: Failed to delete API Gateway after $MAX_RETRIES attempts."
exit 1
