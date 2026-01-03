# GitHub × LINE Bot = GitLine

A LINE Bot that automatically saves notes and images sent via LINE to a GitHub repository.

## Features

- **Text Memo**: Automatically saves text messages to GitHub (append mode)
- **Daily Journal**: Messages starting with date pattern (YYYY/MM/DD or YYYY-MM-DD) are saved as daily entries (overwrite mode)
- **Image Saving**: Automatically saves images to GitHub with markdown links

## Architecture

```
LINE Webhook → AWS Lambda → GitHub API
```

## Setup

### 1. Environment Variables

See [.env.example](.env.example) for required variables:

```bash
# Required
GITHUB_ACCESS_TOKEN=your_github_personal_access_token
GITHUB_USERNAME=your_github_username
GITHUB_REPOSITORY=your_repository_name
LINEBOT_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINEBOT_USER_ID=your_line_user_id

# Optional (with defaults)
NOTE_BASE_DIR=seeds    # Directory for memos
DAILY_BASE_DIR=daily   # Directory for daily journals
```

### 2. Create AWS IAM User (for GitHub Actions)

Create an IAM user with the following AWS managed policies:
- `AmazonEC2ContainerRegistryPowerUser`
- `AWSLambda_FullAccess`

```bash
./create-iam-user.sh
```

Save the output credentials for GitHub Secrets configuration.

### 3. AWS Lambda Deployment

Run the following scripts for initial setup:

```bash
# Create Lambda function
./create-lambda.sh

# Create and configure API Gateway
./create-api-gateway.sh
```

### 4. Lambda Environment Variables

Set environment variables in AWS Lambda console or via CLI:

```bash
aws lambda update-function-configuration \
  --function-name gitline \
  --environment "Variables={
    GITHUB_ACCESS_TOKEN=your_github_personal_access_token,
    GITHUB_USERNAME=your_github_username,
    GITHUB_REPOSITORY=your_repository_name,
    LINEBOT_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token,
    LINEBOT_USER_ID=your_line_user_id,
    NOTE_BASE_DIR=seeds,
    DAILY_BASE_DIR=daily
  }"
```

Or create `.env.production` file and use it for reference:

```bash
# .env.production (do NOT commit this file)
GITHUB_ACCESS_TOKEN=ghp_xxxxxxxxxxxx
GITHUB_USERNAME=your_username
GITHUB_REPOSITORY=your_repo
LINEBOT_CHANNEL_ACCESS_TOKEN=xxxxxxxx
LINEBOT_USER_ID=Uxxxxxxxx
NOTE_BASE_DIR=seeds
DAILY_BASE_DIR=daily
```

### 5. GitHub Actions Configuration

Set the following secrets in your GitHub repository:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `ECR_REPOSITORY`
- `LAMBDA_FUNCTION_NAME`

## Usage

### Text Note

Send any text message to the LINE Bot. It will be saved to:
```
{NOTE_BASE_DIR}/{year}/{month}/{month}{day}.md
```

Multiple messages on the same day are appended with `---` separator.

### Daily Journal

Send a message starting with a date pattern:
```
2026/01/03 Today's journal entry...
2026-01-03 Another format works too...
```

It will be saved to:
```
{DAILY_BASE_DIR}/{year}/{month}/{month}{day}.md
```

Daily entries overwrite previous content for the same date.

### Image

Send an image to the LINE Bot. It will be:
1. Saved to `{NOTE_BASE_DIR}/{year}/{month}/assets/{timestamp}.jpg`
2. A markdown link added to the day's memo

## File Structure

### Project Structure

```
├── app.py              # Lambda handler (LINE Bot)
├── src/
│   ├── note.py         # NoteRegistry class
│   └── daily.py        # DailyRegistry class
├── .github/
│   └── workflows/
│       └── deploy.yml  # Auto-deploy on push
├── requirements.txt
├── Dockerfile
├── create-iam-user.sh  # IAM user setup for GitHub Actions
└── create-lambda.sh    # Lambda function setup
```

### GitHub Repository Structure (Output)

```
your-repository/
├── seeds/                          # NOTE_BASE_DIR (notes & images)
│   └── {year}/
│       └── {month}/
│           ├── {month}{day}.md     # Daily note (e.g., 0103.md)
│           └── assets/
│               └── {year}-{month}-{day}-{HHMMSS}.jpg # Uploaded images (e.g., 2026-01-03-142757.jpg)
└── daily/                          # DAILY_BASE_DIR (journals)
    └── {year}/
        └── {month}/
            └── {month}{day}.md     # Daily journal (e.g., 0103.md)
```

Example:
```
your-repository/
├── seeds/
│   └── 2026/
│       └── 01/
│           ├── 0103.md
│           ├── 0104.md
│           └── assets/
│               ├── 2026-01-03-142708.jpg
│               └── 2026-01-04-091523.jpg
└── daily/
    └── 2026/
        └── 01/
            ├── 0103.md
            └── 0104.md
```

## Deployment

Automatically deployed to AWS Lambda via GitHub Actions when pushed to `main` branch.

### Manual Deployment

```bash
# Login to ECR
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="ap-northeast-1"
FUNCTION_NAME="gitline"

aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Build and push
docker build -t $FUNCTION_NAME .
docker tag $FUNCTION_NAME:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$FUNCTION_NAME:latest
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$FUNCTION_NAME:latest

# Update Lambda
aws lambda update-function-code \
  --function-name $FUNCTION_NAME \
  --image-uri $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$FUNCTION_NAME:latest
```

## Troubleshooting

### 502 Bad Gateway

Ensure the Lambda function returns proper HTTP response (statusCode: 200).

### Memo Not Saving

- Check GitHub Personal Access Token permissions
- Verify repository name and username are correct
