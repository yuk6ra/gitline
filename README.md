# Github Line Note

```
$ aws ecr create-repository --repository-name line-git-note-save-note
$ docker build -t line-git-note-save-note .
$ docker tag accounting:latest <>.dkr.ecr.ap-northeast-1.amazonaws.com/accounting:latest
$ docker push <>.dkr.ecr.ap-northeast-1.amazonaws.com/accounting:latest
```

aws iam create-user --user-name github-actions-lambda-deploy

aws iam create-policy \
--policy-name GitHubActionsLambdaDeployPolicy \
--policy-document file://aws/iam-policy.json

aws iam attach-user-policy \
    --user-name github-actions-lambda-deploy \
    --policy-arn arn:aws:iam::<Account ID>:policy/GitHubActionsLambdaDeployPolicy

aws iam create-access-key --user-name github-actions-lambda-deploy