# Oracle AI

A LINE Bot that automatically saves memos sent via LINE to a GitHub repository and provides AI-powered deep-dive questioning functionality.

## Features

- **Memo Saving**: Automatically saves text sent via LINE to a GitHub repository
- **AI Deep-dive**: Generates questions about memos using OpenAI GPT
- **Interactive Sessions**: Deep exploration of memos through question-and-answer interactions
- **Objective Analysis**: AI-powered objective analysis and insights on memos
- **Session Management**: Interactive sessions with timeout functionality

## Architecture

```
LINE Webhook → AWS Lambda → GitHub API
                    ↓
                OpenAI API
```

## Setup

### 1. Required Environment Variables

Set the following environment variables:

```bash
# LINE Bot Configuration
LINEBOT_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINEBOT_USER_ID=your_line_user_id

# GitHub Configuration
GITHUB_ACCESS_TOKEN=your_github_personal_access_token
GITHUB_USERNAME=your_github_username
GITHUB_REPOSITORY=your_repository_name

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key
```

### 2. Create AWS IAM User (for GitHub Actions)

```bash
# Create IAM user
aws iam create-user --user-name github-actions-lambda-deploy

# Create policy
aws iam create-policy \
  --policy-name GitHubActionsLambdaDeployPolicy \
  --policy-document file://aws/iam-policy.json

# Attach policy to user
aws iam attach-user-policy \
  --user-name github-actions-lambda-deploy \
  --policy-arn arn:aws:iam::<Account-ID>:policy/GitHubActionsLambdaDeployPolicy

# Create access key
aws iam create-access-key --user-name github-actions-lambda-deploy
```

### 3. AWS Lambda Deployment

Run the following scripts for initial setup:

```bash
# Create Lambda function
./create-lambda.sh

# Create and configure API Gateway
./create-api-gateway.sh
```

### 4. GitHub Actions Configuration

Set the following secrets in your GitHub repository:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `LINEBOT_CHANNEL_ACCESS_TOKEN`
- `LINEBOT_USER_ID`
- `GITHUB_ACCESS_TOKEN`
- `GITHUB_USERNAME`
- `GITHUB_REPOSITORY`
- `OPENAI_API_KEY`

## Usage

### Basic Memo Saving

1. Send a message to the LINE Bot
2. When asked "Do you want to deep-dive?"
3. Input anything other than "yes" to save as a regular memo

### AI Deep-dive Session

1. Input "yes" after sending a memo
2. Select from AI-generated questions (respond with numbers 1-5)
3. Answer the questions
4. Can continue with "Do you want to continue deep-diving?"
5. Up to 10 question-and-answer rounds possible

### Special Commands

- **Reconsider**: Regenerate questions from different angles
- **End**: Force end the session
- **AI Analysis**: Get objective analysis from AI

## Development

### Local Testing

```bash
python app.py
```

Runs in local test mode when environment variables are not set.

### File Structure

```
├── app.py              # Main processing (Lambda function)
├── src/
│   └── note.py         # GitHub API & AI processing
├── aws/
│   ├── iam-policy.json # IAM policy
│   └── lambda-trust-policy.json
├── requirements.txt    # Python dependencies
├── Dockerfile         # Container configuration
└── create-*.sh        # Deployment scripts
```

## Deployment

Automatically deployed to AWS Lambda via GitHub Actions when pushed.

### Manual Deployment (using ECR)

```bash
# Create ECR repository
aws ecr create-repository --repository-name line-git-note-save-note

# Build and push Docker image
docker build -t line-git-note-save-note .
docker tag line-git-note-save-note:latest <account-id>.dkr.ecr.ap-northeast-1.amazonaws.com/line-git-note-save-note:latest
docker push <account-id>.dkr.ecr.ap-northeast-1.amazonaws.com/line-git-note-save-note:latest
```

## Troubleshooting

### 502 Bad Gateway

Ensure the Lambda function returns proper HTTP response (statusCode: 200).

### Memo Not Saving

- Check GitHub Personal Access Token permissions
- Verify repository name and username are correct

### AI Features Not Working

- Verify OpenAI API Key is valid
- Check if API usage limits have been reached
