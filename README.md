# Github Line Note

```
$ aws ecr create-repository --repository-name line-git-note-save-note
$ docker build -t line-git-note-save-note .
$ docker tag accounting:latest <>.dkr.ecr.ap-northeast-1.amazonaws.com/accounting:latest
$ docker push <>.dkr.ecr.ap-northeast-1.amazonaws.com/accounting:latest
```