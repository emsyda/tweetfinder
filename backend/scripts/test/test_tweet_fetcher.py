from scripts.fetch_and_save_tweets import main
import os
import sys
import pytest

from dotenv import load_dotenv
load_dotenv('.env.local')


credentials = {
    'consumer_key': os.environ["CONSUMER_KEY"],
    'consumer_secret': os.environ["CONSUMER_SECRET"],
    'access_token': os.environ["ACCESS_TOKEN"],
    'access_token_secret': os.environ["ACCESS_TOKEN_SECRET"]
}

@pytest.fixture(autouse=True, scope="module")
def setup():
    # code to set up fixture
    sys.argv = [sys.argv[0],
        #'paulfchristiano',
        'bertcmiller',
        #'ESYudkowsky',
        '--test',
        '--no-mongo',
        #'--force-end-id=1521871942457820000', # 748 retweets+likes
        *list(credentials.values())
    ]
    yield
    # code to tear down fixture



def test_fetch_and_save_tweets():
    main()
