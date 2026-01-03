#!/bin/bash
set -e  # エラー時に停止

# 引数チェック
if [ -z "$1" ]; then
  echo "Usage: $0 <function-name>"
  echo "Example: $0 oracle-ai"
  exit 1
fi

# 環境変数
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="ap-northeast-1"
FUNCTION_NAME="$1"
API_NAME="${FUNCTION_NAME}-api"

echo "Account ID: $ACCOUNT_ID"
echo "Region: $REGION"
echo "Function Name: $FUNCTION_NAME"
echo "API Name: $API_NAME"

# 1. REST API作成
echo "Creating REST API..."
API_ID=$(aws apigateway create-rest-api --name $API_NAME --query 'id' --output text)
echo "API ID: $API_ID"

# 2. ルートリソースID取得
PARENT_ID=$(aws apigateway get-resources --rest-api-id $API_ID --query 'items[?path==`/`].id' --output text)
echo "Parent Resource ID: $PARENT_ID"

# 3. /webhook リソース作成
echo "Creating /webhook resource..."
RESOURCE_ID=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $PARENT_ID \
  --path-part webhook \
  --query 'id' --output text)
echo "Webhook Resource ID: $RESOURCE_ID"

# 4. POSTメソッド追加
echo "Adding POST method..."
aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $RESOURCE_ID \
  --http-method POST \
  --authorization-type NONE

# 5. Lambda統合設定
echo "Setting up Lambda integration..."
LAMBDA_URI="arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$FUNCTION_NAME/invocations"

aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $RESOURCE_ID \
  --http-method POST \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri $LAMBDA_URI

# 6. メソッドレスポンス設定
echo "Setting up method response..."
aws apigateway put-method-response \
  --rest-api-id $API_ID \
  --resource-id $RESOURCE_ID \
  --http-method POST \
  --status-code 200

# 7. 統合レスポンス設定
echo "Setting up integration response..."
aws apigateway put-integration-response \
  --rest-api-id $API_ID \
  --resource-id $RESOURCE_ID \
  --http-method POST \
  --status-code 200

# 8. Lambda実行権限をAPI Gatewayに付与
echo "Adding Lambda permission for API Gateway..."
aws lambda add-permission \
  --function-name $FUNCTION_NAME \
  --statement-id apigateway-invoke-$(date +%s) \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:$REGION:$ACCOUNT_ID:$API_ID/*/*"

# 9. API デプロイ
echo "Deploying API..."
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod

# 10. エンドポイントURL表示
ENDPOINT_URL="https://$API_ID.execute-api.$REGION.amazonaws.com/prod/webhook"
echo ""
echo "✅ API Gateway created successfully!"
echo "📍 Webhook URL: $ENDPOINT_URL"
echo ""
echo "🔧 LINE Developer Console設定:"
echo "  Webhook URL: $ENDPOINT_URL"
echo "  Use SSL: Yes"
echo ""
echo "🧪 テスト用cURLコマンド:"
echo "curl -X POST $ENDPOINT_URL -H 'Content-Type: application/json' -d '{\"events\":[{\"type\":\"message\",\"message\":{\"type\":\"text\",\"text\":\"テスト\"}}]}'"