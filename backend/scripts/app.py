from scripts.embeddings import query as _query, EmbeddingsGenerator
from scripts.fetch_and_save_tweets import TweetFetcher, get_tweet
from scripts.llm import extract_info, modify_filters, info_template
from flask import Flask, request, jsonify, redirect, url_for, session
from flask_oauthlib.client import OAuth
from functools import wraps
from dateutil.parser import parse as parsedate
from datetime import datetime, timedelta
import time
from collections import defaultdict
import binascii
import json
import os
import tweepy
from subprocess import Popen
from threading import Thread
from queue import Queue
import logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
# used to encrypt session cookies. changing it will invalidate all existing sessions
# generated with os.urandom(16).hex(), now unhexlify back to bytes
app.config['SECRET_KEY'] = binascii.unhexlify(os.environ['FLASK_SECRET_KEY'])

oauth = OAuth(app)
twitter = oauth.remote_app(
    'twitter',
    consumer_key=os.environ['CONSUMER_KEY'],
    consumer_secret=os.environ['CONSUMER_SECRET'],
    base_url='https://api.twitter.com/1.1/',
    request_token_url='https://api.twitter.com/oauth/request_token',
    access_token_url='https://api.twitter.com/oauth/access_token',
    authorize_url='https://api.twitter.com/oauth/authenticate'
)

# each user has their own fether & embedder to avoid
#   1. accidental openai api key mixups (in this case between admin & user, as admin can access user's screen_name)
#   2. thread safety (multiple users accessing the same object at the same time)

fetcher_objs: dict[str, dict[str, TweetFetcher]] = defaultdict(dict)
    # user: {screen_name: tweetfetcher}

emb_objs: dict[str, dict[str, EmbeddingsGenerator]] = defaultdict(dict)
    # user: {screen_name: embeddings_generator}

in_progress_processes = {

}
    
# the last time the user's tweets were fetched
last_updated = defaultdict(float) # screen_name: timestamp (sec)
my_thread = None
update_queue = Queue()


def add_object(which, user, screen_name, credentials, openai_api_key, reload=False):
    if which == "fetcher":
        if screen_name not in fetcher_objs[user] or reload:
            #auth = tweepy.OAuth1UserHandler(*credentials)
            #api = tweepy.API(auth)
            fetcher_objs[user][screen_name] = TweetFetcher(None, screen_name, use_mongo=True, test=False, user_id='123')
    elif which == "embedder":
        if screen_name not in emb_objs[user] or reload:
            embeddings_generator = EmbeddingsGenerator(screen_name, openai_api_key, test=False)
            emb_objs[user][screen_name] = embeddings_generator
    else:
        raise ValueError(f"Invalid object type: {which}")


@app.route('/aha')
def home():
    #return "aha"                       # js fetch() can't parse
    #return json.dumps("aha")           # js fetch() can't parse
    return jsonify("aha")               # --> "aha"
    #return ["aha","oho"]               # --> ["aha","oho"]
    #return json.dumps(["aha","oho"])   # --> ["aha","oho"]
    #return jsonify(["aha","oho"])      # --> ["aha","oho"]

@app.route('/testConn', methods=['POST'])
def test_conn():
    # request.args: the key/value pairs in the URL query string
    # request.form: the key/value pairs in the body, from a HTML post form, or JavaScript request that isn't JSON encoded
    # request.values: combined args and form, preferring args if keys overlap
    # request.json: parsed JSON data. The request must have the application/json content type, or use request.get_json(force=True) to ignore the content type.
    # request.files: the files in the body, which Flask keeps separate from form. HTML forms must use enctype=multipart/form-data or files will not be uploaded.
    print(request.args, request.form, request.values, request.json, request.files)
    # ImmutableMultiDict([]) ImmutableMultiDict([]) CombinedMultiDict([ImmutableMultiDict([]), ImmutableMultiDict([])]) {'msg': ['xyz', '123']} ImmutableMultiDict([])
    #return jsonify(f"(testConn) Flask app received this value under 'msg' key: {request.json['msg']}")
    return request.json['msg']


def _get_my_url():
    scheme = request.headers.get('X-Forwarded-Proto', 'http')
    #host = request.headers.get('Host', request.host)  # nah request.host is the initial destination, not the redirected proxy destination
    #return f"{scheme}://{host}"  # {request.full_path}
    return request.headers.get('proxy-pass', '')  # only works in production

@app.route('/getUrl', methods=['GET'])
def get_url():
    return jsonify(_get_my_url())

# --------- LOGIN -----------

@app.route('/')
def index():
    if 'twitter_oauth' in session:
        print('/ OAUTH IN SESSION: ', session['twitter_oauth'])
        """# {'oauth_token': '...', 'oauth_token_secret': '...', 'user_id': '123...', 'screen_name': 'randomUser'}
        me = twitter.get('account/settings.json')
        # https://developer.twitter.com/en/docs/twitter-api/v1/accounts-and-users/manage-account-settings/api-reference/get-account-settings
        # {
        #   "code": 220,
        #   "message": "Your credentials do not allow access to this resource."
        # }
        # Tried with "Read", and "Read, write" access. Maybe DM access is also needed?
        return jsonify({"data": me.data})"""
        # session object is context-specific, it's sent by the client by each request and is basically its browser's cookie
        # https://flask.palletsprojects.com/en/2.0.x/quickstart/#sessions
        # the cookie is encrypted/decrypted with app's SECRET_KEY. nothing is stored on the server (besides the SECRET_KEY)
        # the client itself can't see/modify the cookie's contents due to the encryption
        return _get_login_status()
    return redirect(url_for('login'))


@app.route('/login')
def login():
    callback_url = url_for('oauthorized', _external=True)
    print("CALLBACK URL: ", callback_url, "request.referrer", request.referrer)
    return twitter.authorize(callback=callback_url or request.referrer or None)


@app.route('/oauthorized')
@twitter.authorized_handler
def oauthorized(resp):
    print("/oauthorized RESPONSE: ", resp)
    if resp is None:
        return 'Access denied: reason=%s error=%s' % (
            request.args['oauth_problem'],
            request.args['error_description']
        )
    session['twitter_oauth'] = resp
    return redirect(url_for('index'))


@twitter.tokengetter
def get_twitter_token(token=None):
    print("get_twitter_token(): twitter_oauth: ", session.get('twitter_oauth'))
    return session.get('twitter_oauth')


@app.route('/getLoginStatus')
def get_login_status():
    _start_thread()
    if _is_logged_in():
        # signal to start pulling user's tweets
        update_queue.put((_get_user(), _get_user(), _get_credentials()))
    return _get_login_status()

@app.route('/logout')
def logout():
    # also sends back the cookie which has the login info removed
    session.pop('twitter_oauth', None)
    return { "success": True}


# --------- LOGIN HELPERS -----------

def _get_login_status():
    key_exists = bool(session.get('openai_api_key'))
    sess_data = {'screen_name': None, 'user_id': None, 'logged_in': False, 'is_admin': False, 'openai_key_stored': key_exists}
    if 'twitter_oauth' in session:
        oauth = session['twitter_oauth']
        screen_name = oauth['screen_name'].lower()
        is_admin = screen_name in os.environ['ADMIN_ACCOUNTS'].lower().split()
        return {**sess_data, 'screen_name': screen_name, 'user_id': oauth['user_id'], 'logged_in': True, 'is_admin': is_admin}
    return sess_data

def _get_user():
    return _get_login_status()['screen_name']

def _is_logged_in():
    return 'twitter_oauth' in session


def auth(clearance, required_session_vars=[]):
    if clearance not in ['admin', 'user']:
        raise ValueError("clearance must be 'admin' or 'user'")
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if clearance:
                if not 'twitter_oauth' in session:
                    return jsonify({'error': 'Login required'}), 403
                elif clearance == 'admin' and not _get_login_status()['is_admin']:
                    return jsonify({'error': 'Admin only'}), 403
            if request.json.get('openai_api_key'):
                session['openai_api_key'] = request.json.pop('openai_api_key')
            missing_session_vars = [x for x in required_session_vars if not session.get(x)]
            if missing_session_vars:
                return jsonify({'error': f"Missing required session variable(s): {json.dumps(missing_session_vars)}"}), 400
            return f(*args, **kwargs)
        return decorated_function
    return wrapper


def validate(required=[], session_required=[]):
    def wrapper(f):
        @wraps(f) # this line is necessary or flask crashes
        def decorated_function(*args, **kwargs):
            status = _get_login_status()
            # only admin can pull / search tweets of other users
            if not status['is_admin']:
                request.json['screen_name'] = status['screen_name']
            if request.json.get('screen_name'):
                request.json['screen_name'] = request.json['screen_name'].lower()
            missing_params = [x for x in required if not request.json.get(x)]
            if missing_params:
                return jsonify({'error': f"Missing required parameter(s): {json.dumps(missing_params)}"}), 400
            return f(*args, **kwargs)
        return decorated_function
    return wrapper


def _get_credentials():
    credentials = [os.environ["CONSUMER_KEY"], os.environ["CONSUMER_SECRET"]]
    if 'twitter_oauth' in session:
        oauth = session['twitter_oauth']
        credentials += [oauth['oauth_token'], oauth['oauth_token_secret']]
    return credentials

# --------- APP -----------

@app.route('/getNearestTweets', methods=['POST'])
@auth('user', ['openai_api_key'])
@validate(['screen_name'])
def get_nearest_tweets():
    print(request.json)
    qry = request.json['query']
    screen_name = request.json['screen_name']
    k = min(request.json['k'], 10)
    filters = request.json['filters']
    date_today = (datetime.utcnow() - timedelta(hours=request.json['timezoneOffset'])).strftime('%Y-%m-%d')

    for key in ['before', 'after']:
        if isinstance(filters.get(key), str):
            # check if is number
            try:
                filters[key] = int(filters[key])
            except ValueError:
                dt = parsedate(filters[key])
                # convert datetime to millis
                filters[key] = int(dt.timestamp() * 1000)
    
    if not screen_name:
        return { 'error': "You must enter the username into the bottom text box"}
    
    if in_progress_processes.get(screen_name):
        return { 'error': f"Tweets of '{screen_name}' are currently being updated" }
    
    add_object('fetcher', _get_user(), screen_name, _get_credentials(), None)
    add_object('embedder', _get_user(), screen_name, None, session['openai_api_key']) # embeddings will be generated here
    fetcher = fetcher_objs[_get_user()][screen_name]

    # otherwise chroma prints out many annoying "Chroma collection paulfchristiano contains fewer than {k} elements" warnings
    k = min(len(fetcher.tweets), k)
    
    info = info_template()
    if qry:
        info = extract_info(qry, date_today)
    print("extracted info:", {k: v for k, v in info.items() if v})

    if info['topic']:
        qry = info['topic']
    
    filters = modify_filters(filters, info)
    print(f'modified filters: {filters}')
    
    filtered_tweets = []
    for tweet in fetcher.tweets:
        result = fetcher._filter_tweet(tweet, filters)
        if result['ok']:
            filtered_tweets.append(tweet)
            tweet['matching_words'] = result['matches']
    #print(filtered_tweets)
    

    if qry:
        tweets = _query(screen_name, qry, k=k, test=False, tweets=filtered_tweets,
                        embeddings_generator=emb_objs[_get_user()][screen_name])
    else:
        tweets = filtered_tweets[:k]

    return { 'tweets': tweets }


@app.route('/pullTweets', methods=['POST'])
@auth('admin')
@validate(['screen_name'])
def pull_tweets():
    print(request.json)
    screen_name = request.json['screen_name'] 
    return _pull_tweets(_get_user(), screen_name, _get_credentials())


def _pull_tweets(user, screen_name, credentials):
    if in_progress_processes.get(screen_name):
        return { 'error': f"{screen_name} tweets are already currently being updated" }
    
    last_updated[screen_name] = time.time()

    try:
        in_progress_processes[screen_name] = True
        print(f"Starting fetch_and_save_tweets.py process for {screen_name}")
        process = Popen([os.environ.get('PYTHONEXECUTABLE', '.venv/bin/python3'),
            "-m", "scripts.fetch_and_save_tweets", screen_name, *credentials
        ])
        # wait till process is finished
        process.wait()
        print(f"Finished fetch_and_save_tweets.py process for {screen_name}")
        
        add_object('fetcher', user, screen_name, credentials, None, reload=True)
        emb_objs[user].pop(screen_name, None)
    finally:
        in_progress_processes[screen_name] = False
    
    return { 'status': 'success' }


def _start_thread():
    global my_thread
    if my_thread is None:
        my_thread = Thread(target=_updater, daemon=True)
        my_thread.start()


def _updater():
    print("Starting updater thread")
    while True:
        (user, screen_name, credentials) = update_queue.get()
        try:
            print(f"Updater: request to pull tweets for {screen_name} (initiated by {user})")
            if time.time() - last_updated[screen_name] < 7200:
                print(f"Updater: skipping {screen_name} because it was updated recently")
                continue 
            _pull_tweets(user, screen_name, credentials)
        except Exception as e:
            logging.exception(e)
            print(f"Error pulling tweets for {screen_name} (initiated by {user})")
    print("Ending updater thread")


if __name__ == '__main__':
    # host: by default 127.0.0.1 (localhost), set to 0.0.0.0 to be accessible from any IP address (on docker and production stage)
    # port: by default 5000, set to 3001 for local development
    app.run(host=os.environ.get('HOST', '127.0.0.1'), port=os.environ.get('PORT', 3001), threaded=True, debug=True)

