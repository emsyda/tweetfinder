

function filterTweets(tweets, message, retweeted, quoteTweeted, liked) {
    if (message) {
        tweets = tweets.filter((tweet) => {
            return tweet.text.toLowerCase().includes(message.toLowerCase());
        });
    }
    if (retweeted) {
        tweets = tweets.filter((tweet) => {
            return tweet.is_retweet;
        });
    }
    if (quoteTweeted) {
        tweets = tweets.filter((tweet) => {
            return tweet.is_quote;
        });
    }
    if (liked) {
        tweets = tweets.filter((tweet) => {
            return tweet.is_quote;
        });
    }
    console.log(tweets)
    return tweets;
}
