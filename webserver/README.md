
## Instructions to deploy to an environment

Please use the registry name (rg-name) that's designated for an environment:

```
az login
az acr login --name rg-name
docker build -f Dockerfile -t flk_gpt/backend:latest .
docker tag flk_gpt/backend:latest  rg-name.azurecr.io/flk_gpt/backend:latest
docker push rg-name.azurecr.io/flk_gpt/backend:latest
```