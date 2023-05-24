source .env.local

# docker tag <image-name> <acr-login-server>/<image-name>
docker tag tweetfinder-backend:latest $ACR_REGISTRY_ID/tweetfinder-backend:latest
docker tag tweetfinder-frontend:latest $ACR_REGISTRY_ID/tweetfinder-frontend:latest

#docker push <acr-login-server>/<image-name>
docker push $ACR_REGISTRY_ID/tweetfinder-backend:latest
docker push $ACR_REGISTRY_ID/tweetfinder-frontend:latest
