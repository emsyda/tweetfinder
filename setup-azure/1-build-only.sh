#!/bin/bash

docker build -t tweetfinder-backend:latest ../backend
docker build -t tweetfinder-frontend:latest ../frontend
