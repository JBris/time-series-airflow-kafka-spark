#!/usr/bin/env bash

docker compose exec mlflow bentoml serve --host 0.0.0.0 -p 3000 aks.examples.5_deploy_online_model:svc
