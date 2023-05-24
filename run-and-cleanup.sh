#!/bin/bash
# envs for the docker-compose file
source .env.local

# check if volume tweetfinder exists, if not, create
output=$(docker volume ls --filter name=tweetfinder | grep tweetfinder)
if [ -z "$output" ]; then
    echo "Creating 'tweetfinder' volume"
    docker volume create tweetfinder
fi


# mongo and tweetfinder containers must be on the same network, otherwise they can't communicate with each other
#   (although from the host machine I can connect to any of them via localhost:port)
output=$(docker network ls --filter name=custom | grep custom)
if [ -z "$output" ]; then
    echo "Creating 'custom' network"
    docker network create custom
fi


# check if mongo container is running, if not, create/start
output=$(docker ps --filter name=mongo | grep mongo)
output_all=$(docker ps -all --filter name=mongo | grep mongo)
if [ -z "$output" ]; then
    if [ -z "$output_all" ]; then
        echo "MongoDB container not found"
        echo "Creating MongoDB container"
        docker run --name mongo -p 27017:27017 --network custom -d mongo
    else
        echo "Starting MongoDB container (that was previously stopped)"
        docker start mongo
    fi
fi

#services="backend frontend"
docker-compose up --build
# delete docker container
docker-compose down --rmi all
