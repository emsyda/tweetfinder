from scripts.types import Tweet
from scripts.utils import get_current_env
import csv
import tweepy
import pymongo
import time
import sys
import os
import re
from difflib import get_close_matches
import argparse
from datetime import datetime

DATA_DIR = 'data/'
DATA_DIR_TEST = '.test/data/'
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(DATA_DIR_TEST, exist_ok=True)


class TweetFetcher:
    CSV_HEADER = ['id', 'created_at', 'author', 'in_reply_to', 'text', 'is_retweet', 'is_quote', 'is_liked']
    RTL_COLUMNS = ['is_retweet', 'is_quote', 'is_liked']
    
    
    def __init__(self,
                 api: tweepy.API,
                 screen_name: str,
                 use_mongo=False, *,
                 test=False,
                 force_end_id: str|None = None,
                 user_id: str|None = None):
        
        self.api = api
        self.screen_name = screen_name
        self.user_id = self._resolve_user_id() if not user_id else user_id
        self.force_end_id = force_end_id
        self.covered_ranges = {
            'screen_name': self.screen_name.lower(),
            'likes': [],
            'tweets': []
        }
        self.csv_file_path = self.get_csv_path(screen_name, test=test)
        self.db_name = f'twittydotai_{get_current_env()}' + ('_test' if test else '')
        self.tweets: list[Tweet] = []
        self.client = None
        if use_mongo:
            is_production = get_current_env() == 'production'
            var_name = 'MONGO_URI' if is_production else 'MONGO_URI_DEV'
            mongo_uri = os.environ.get(var_name, 'mongodb://localhost:27017/')
            print(f"Connecting to MongoDB at {mongo_uri}")
            # mongodb://[username:password@]host1[:port1][,...hostN[:portN]][/[defaultauthdb][?options]]
            self.client = pymongo.MongoClient(mongo_uri)
        self.load_tweets()
        self.load_ranges()
        
    def run(self):
        try:
            self.fetch_all('tweets')
            self.fetch_all('likes')
        finally:
            self.save_tweets()
            self.save_ranges()


    def fetch_all(self, which='tweets'):
        is_final = False
        num_request = 0
        while not is_final:
            range, is_final = self.get_middle_range(which)
            try:
                self.fetch_tweets(range[0], range[1], which)
            finally:
                print(self.covered_ranges[which])
                self.flatten_ranges()
                print(self.covered_ranges[which])
                num_request += 1
        print(f"Finished fetching tweets for '{which}', made {num_request} requests")


    def fetch_tweets(self, end_id: str, start_id: str, which='tweets'):
        """Fetch them backwards, end_id --> start_id"""
        print(f"Fetching {which}, end_id={end_id}, start_id={start_id}")
        max_id = end_id
        while True:
            print(f"Fetching {which} from {max_id}")
            params = {'user_id': self.user_id, 'count': 200, 'tweet_mode': 'extended'}
            if max_id is not None:
                params['max_id'] = max_id
            method = self.api.user_timeline if which == 'tweets' else self.api.get_favorites
            tweets = method(**params)
            tweets.sort(key=lambda tweet: int(tweet.id_str), reverse=True)
            self.covered_ranges[which].append(
                [int(max_id) if max_id is not None else (int(tweets[0].id_str) if tweets else 0),
                 int(tweets[-1].id_str) if tweets else 0])
            if len(tweets) == 0:
                break
            for tweet in tweets:
                if which == 'tweets':
                    self.handle_tweet_or_retweet(tweet)
                else:
                    self.handle_like(tweet)
                max_id = str(int(tweet.id_str) - 1)
            print(self.tweets[-1])
            time.sleep(5)
            if int(max_id) < start_id:
                break
    
    def handle_tweet_or_retweet(self, tweet):
        in_reply_to, text_body = self.split_tweet_text(tweet.full_text)
        if getattr(tweet, 'retweeted_status', None):
            retweeted_status = tweet.retweeted_status
            retweeted_status
            self.tweets.append(TweetFetcher.convert_row_to_tweet([
                retweeted_status.id_str,
                retweeted_status.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                retweeted_status.author.screen_name,
                retweeted_status.in_reply_to_screen_name,
                text_body,
                True,
                tweet.is_quote_status,
                False
            ]))
        else:
            # TODO: Fetch and save the quoted tweet as well
            # https://stackoverflow.com/questions/50503326/why-is-tweepy-saying-a-retweet-is-a-quote
            self.tweets.append(TweetFetcher.convert_row_to_tweet([
                tweet.id_str,
                tweet.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                tweet.author.screen_name,
                tweet.in_reply_to_screen_name,
                text_body,
                False,
                tweet.is_quote_status,
                False
            ]))

    # what would a simultaneously retweeted and liked tweet look like?
    #   (probably rare, doesn't matter for now)
    def handle_like(self, tweet):
        in_reply_to, text_body = self.split_tweet_text(tweet.full_text)
        self.tweets.append(TweetFetcher.convert_row_to_tweet([
            tweet.id_str,
            tweet.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            tweet.author.screen_name,
            tweet.in_reply_to_screen_name,
            text_body,
            False,
            tweet.is_quote_status,
            True,
        ]))
    
    def sort(self, reverse=True):
        # sort the tweets by tweet id
        self.tweets.sort(key=lambda tweet: int(tweet['id']), reverse=reverse)
        # remove duplicate tweets
        seen = set()
        for i in range(len(self.tweets)-1, -1, -1):
            if self.tweets[i]['id'] in seen:
                del self.tweets[i]
            else:
                seen.add(self.tweets[i]['id'])
    
    def load_tweets(self):
        try:
            # Read the already saved tweets
            with open (self.csv_file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader)
                rows = list(reader)
                tweets = []
                for i in range(len(rows)):
                    tweet = self.convert_row_to_tweet(rows[i])
                    tweet.update({k: tweet[k].lower() == 'true' for k in TweetFetcher.RTL_COLUMNS})
                    tweets.append(tweet)
                self.tweets += tweets
                self.sort()
        except FileNotFoundError as e:
            print(f"File {self.csv_file_path} not found.")
            self.clear_cache()

    def save_tweets(self):
        self.sort()
        print(f"Saving tweets to {self.csv_file_path}. Number of tweets: {len(self.tweets)}")
        # Open CSV file and write header row
        with open(self.csv_file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(TweetFetcher.CSV_HEADER)
            print("Writing the rows")
            # write the rows to the CSV file
            writer.writerows([[x[k] for k in TweetFetcher.CSV_HEADER] for x in self.tweets])
    

    def flatten_ranges(self):
        """Flatten the ranges of tweets covered by the fetcher"""
        def drop_overlapping(range_2, range_1):
            if range_2[1] > range_1[0] + 1:
                return [range_2, range_1]
            elif range_2[1] > range_1[1]:
                return [[range_2[0], range_1[1]]]
            else:
                return [range_2]
        for key in ['likes', 'tweets']:
            ranges = self.covered_ranges[key]
            ranges.sort(key=lambda r: (r[0], r[1]), reverse=True)
            new_ranges = ranges[:1]
            for i in range(1, len(ranges)):
                add = drop_overlapping(new_ranges[-1], ranges[i])
                new_ranges[-1] = add[0]
                new_ranges.extend(add[1:])
            self.covered_ranges[key] = new_ranges
    
    def get_middle_range(self, key):
        ranges = self.covered_ranges[key]
        if not ranges:
            range = [None, 0]
        elif len(ranges) == 1:
            if ranges[0][1] == 0:
                range = [None, ranges[0][0] + 1]
            else:
                range = [ranges[0][1]-1, 0]
        else:
            range = [ranges[0][1]-1, ranges[1][0]+1]
        
        is_final = range[0] is None 

        # For testing purposes (reduce the number of tweets fetched)
        if self.force_end_id is not None:
            if range[0] is None or range[0] > self.force_end_id:
                range[0] = self.force_end_id
            if range[1] is None or range[1] > self.force_end_id:
                range[1] = 0
            is_final = range[0] == self.force_end_id
        
        return range, is_final
                

    def load_ranges(self):
        if self.client:
            covered_ranges = self.client[self.db_name]['covered_ranges'].find_one(
                {'screen_name': self.screen_name.lower()}
            )
            print(f"Mongodb returned covered ranges: {covered_ranges}")
            if covered_ranges is not None:
                self.covered_ranges.update(
                    covered_ranges
                )
        else:
            tweets = [x for x in self.tweets if not x['is_liked']]
            likes = [x for x in self.tweets if x['is_liked']]
            self.covered_ranges.update({
                'likes': [[int(likes[0]['id']), int(likes[-1]['id'])]] if likes else [],
                'tweets': [[int(tweets[0]['id']), int(tweets[-1]['id'])]] if tweets else []
            })
            print(f"Covered ranges from CSV: {self.covered_ranges}")
    
    def save_ranges(self):
        self.flatten_ranges()
        if self.client:
            self.client[self.db_name]['covered_ranges'].update_one(
                {'screen_name': self.screen_name.lower()}, {"$set": self.covered_ranges}, upsert=True
            )
    
    def clear_cache(self):
        if self.client:
            print(f"Clearing cache for {self.screen_name}")
            self.client[self.db_name]['covered_ranges'].delete_one(
                {'screen_name': self.screen_name.lower()}
            )
    

    def _resolve_user_id(self):
        """Look up user ID of a twitter handle"""
        user = self.api.get_user(screen_name=self.screen_name)
        return user.id_str
    

    def filter_tweets(self, options=None):
        """Filter the tweets based on the options"""
        return TweetFetcher._filter_tweets(self.tweets, options)


    @staticmethod
    def _filter_tweets(tweets: list[Tweet], options=None):
        if not options:
            return tweets[:]
        return [tweet for tweet in tweets if TweetFetcher._filter_tweet(tweet, options)['ok']]
    

    def get_tweet(self, id):
        """Get a tweet by its ID"""
        return TweetFetcher._get_tweet(self.tweets, id)
    

    @staticmethod
    def _get_tweet(tweets, id):
        try:
            return next(tweet for tweet in tweets if tweet['id'] == id)
        except StopIteration:
            raise ValueError(f"Tweet with id {id} hasn't been recorded here")
    

    @staticmethod
    def get_csv_path(screen_name, *, test=False):
        data_dir = DATA_DIR_TEST if test else DATA_DIR
        return data_dir + f'tweets_{screen_name.lower()}.csv'
    
    @staticmethod
    def convert_row_to_tweet(row):
        return dict(zip(TweetFetcher.CSV_HEADER, row),
                    timestamp=int(datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S').timestamp() * 1000))

    @staticmethod
    def split_tweet_text(text):
        # get all words before the first words that doesn't befin with @
        first_non_in_reply_to_index = next((i for i,x in enumerate(text.split(' ')) if not x.startswith('@')), -1)
        responds_to = ''
        if first_non_in_reply_to_index != -1:
            responds_to = text.split(' ')[:first_non_in_reply_to_index]
            text = ' '.join(text.split()[first_non_in_reply_to_index:])
        return responds_to, text
    

    @staticmethod
    def _filter_tweet(tweet: Tweet, options=None):
        split_comma = lambda x: re.split(r',\s*', x)
        #n_percent_match = lambda x, y: len(set(x).intersection(y)) / len(x) * 100
        PASSED = True
        options = options or {}
        if options.get('rtl') is not None:
            is_either = tweet['is_retweet'] or tweet['is_liked']
            if options['rtl'] != is_either:
                PASSED = False
        if options.get('is_quote') is not None:
            if options['is_quote'] != tweet['is_quote']:
                PASSED = False
        if options.get('before') is not None:
            if tweet['timestamp'] > options['before']:
                PASSED = False
        if options.get('after') is not None:
            if tweet['timestamp'] < options['after']:
                PASSED = False
    
        for k in ['author', 'in_reply_to']:
            if not options.get(k):
                continue
            choices = split_comma(options[k].lower())
            candidates = [tweet[k].lower()]
            if not tweet[k] or not any(get_close_matches(x, candidates) for x in choices):
                PASSED = False
        
        # suffice if contains any word or any mention
        any_ = {}
        text_split = tweet['text'].lower().split()
        # for later bolding these words out in the UI
        matching_exact_words = []

        # optional_words don't count towards PASSING, just for retrieving their positions
        for k in ['words', 'optional_words']:
            if options.get(k):
                choices = split_comma(options[k].lower())
                any_word = False
                for word in choices:
                    number_of_words = len(word.split())
                    text_by_n_words = [' '.join(text_split[i:i+number_of_words])
                                    for i in range(len(text_split) - number_of_words + 1)]
                    matches = get_close_matches(word, text_by_n_words)
                    if matches:
                        matching_exact_words += matches
                        any_word = True
                if k == 'words':
                    any_['words'] = any_word
        
        if options.get('mentions'):
            choices = split_comma(options['mentions'].lower())
            # omitting taking only @-words because the mention might be by name, not username
            candidates = [w[(1 if w.startswith('@') else 0):] for w in text_split]
            for word in choices:
                matches = get_close_matches(word, candidates)
                if matches:
                    matching_exact_words += matches
                    any_['mentions'] = True
        
        if any_ and not any(any_.values()):
            PASSED = False

        # filter out any symbols from the beginning and end of the word
        matching_exact_words = [re.sub(r"^\W+|\W+$", "", word) for word in matching_exact_words]

        return {'ok': PASSED, 'matches': list(set(matching_exact_words))}



def get_tweet(screen_name_or_tweets, id, *, test=False):
    if isinstance(screen_name_or_tweets, list):
        return TweetFetcher._get_tweet(screen_name_or_tweets, id)
    else:
        tweetfetcher = TweetFetcher(None, screen_name_or_tweets, test=test, user_id='123')
        return tweetfetcher.get_tweet(id)


def main():
    parser = argparse.ArgumentParser()

    # Required argument
    parser.add_argument("screen_name", help="Twitter screen name")

    parser.add_argument("--test", action="store_true", help="Execute in test mode")
    parser.add_argument("--no-mongo", action="store_true", help="Execute in test mode")
    parser.add_argument('--force-end-id', type=int, help="Force the end id of the range to be fetched", default=None)

    parser.add_argument("--command", help="one of: ['run,clear']", choices=['run','clear'], default='run')

    # Remaining arguments for credentials (https://docs.python.org/2/library/argparse.html#nargs)
    # the 2 keys of the app itself
    parser.add_argument('credentials', nargs=2, help='Consumer credentials for accessing Twitter API') # consumer_key, consumer_secret
    # for private timelines. generated by a user granting OAuth1.0 access to the app
    parser.add_argument('access_credentials', nargs='*', help='Access credentials for accessing Twitter API') # access_token, access_token_secret

    args = parser.parse_args()

    print("All arguments: ", args)

    # Authenticate with Twitter API
    #auth = tweepy.OAuth1UserHandler(consumer_key, consumer_secret, access_token, access_token_secret)
    api = None
    user_id = '123'
    if args.command != 'clear':
        auth = tweepy.OAuth1UserHandler(*args.credentials, *args.access_credentials)
        api = tweepy.API(auth)
        user_id = None

    tweetfetcher = TweetFetcher(api, args.screen_name, not args.no_mongo, test=args.test,
                                force_end_id=args.force_end_id, user_id=user_id)
    print(f"Executing command: {args.command}")
    if not args.command or args.command == 'run':
        tweetfetcher.run()
    elif args.command == 'clear':
        tweetfetcher.clear_cache()

    print('Done')


if __name__  == '__main__':
    main()



"""
Status object attributes:
-------------------------
author
contributors                    None    // No info about this
coordinates
created_at
destroy
display_text_range
entities
favorite
favorite_count
favorited
full_text
geo
id
id_str
in_reply_to_screen_name         None
in_reply_to_status_id           None
in_reply_to_status_id_str       None
in_reply_to_user_id             None
in_reply_to_user_id_str         None
is_quote_status
lang
parse
parse_list
place
possibly_sensitive
quoted_status                   <Status>  // In an ORDINARY tweet only that has `is_quote_status=true`
quoted_status_id
quoted_status_id_str
quoted_status_permalink
retweeted_status                <Status>  // In a RETWEET only (not in an ordinary tweet)
retweet                         ??        // Didn't find this one in the timeline's tweets I saw   
retweet_count
retweeted
retweets
source
source_url
truncated
user                            <User>
"""