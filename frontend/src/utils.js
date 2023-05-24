function filterTweets(tweets, message, is_retweet, is_quote, is_liked) {
    /*if (message) {
        tweets = tweets.filter((tweet) => {
            return tweet.text.toLowerCase().includes(message.toLowerCase());
        });
    }*/
    if (is_retweet) {
        tweets = tweets.filter((tweet) => {
            return tweet.is_retweet;
        });
    }
    if (is_quote) {
        tweets = tweets.filter((tweet) => {
            return tweet.is_quote;
        });
    }
    if (is_liked) {
        tweets = tweets.filter((tweet) => {
            return tweet.is_quote;
        });
    }
    //console.log(tweets)
    return tweets;
}



module.exports = {
    filterTweets,
}
