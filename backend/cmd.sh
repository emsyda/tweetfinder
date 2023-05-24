#!/bin/bash
source ../.env.local

python () {
    echo $@
    # pass all args except $0
    .venv/bin/python3 $@
}

listFilesThatArentDirs () {
    files=""
    for file in $1/*; do
        if [ -f "$file" ]; then
            files="$files $file"
        fi
    done
}

# $1 is the command, match it to actions
# the rest of the arguments are passed to the command

case $1 in
    "start")
        python -m scripts.app
        ;;
    "clear")
        # $@ is all arguments     # note that $0 is omitted, i.ee $1 $2 ...
        # ${@:start_index:count}  # note that $0 is NOT omitted, i.e. ${@:0:2} is $0 $1
        python -m scripts.fetch_and_save_tweets ${@:2:10} a b c d --command=clear
        ;;
    "clear_all")
        files=$(listFilesThatArentDirs data)
        # loop through all files, split by spaces
        for file in $files; do
            # file is in format "tweet_<username>.csv", extract the username
            username=$(echo $file | cut -d'_' -f2 | cut -d'.' -f1)
            # remove the file
            python -m scripts.fetch_and_save_tweets ${@:2:10} a b c d --command=clear
            rm $file
        done
        ;;
    "fetch_tweets")
        python -m scripts.fetch_and_save_tweets $2 $CONSUMER_KEY $CONSUMER_SECRET $ACCESS_TOKEN $ACCESS_TOKEN_SECRET
        ;;
    "embeddings")
        python -m scripts.embeddings ${@:2:10} --key $OPENAI_API_KEY
        ;;
    *)
        echo "Unknown command $1"
        exit 1
        ;;
esac
