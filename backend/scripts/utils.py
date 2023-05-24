import dotenv
import os

def load_env(on_production=False):
    # Docker image won't contain the .env.local file
    if not os.environ.get('PYTHON_ENV')=='production' or not on_production:
        dotenv.load_dotenv('../.env.local')
    # To avoid accidental mixup in the tests (wouldn't notice missing cli key if env key is set)
    os.environ.pop('OPENAI_API_KEY', None)


def get_current_env():
    return os.environ.get('PYTHON_ENV', 'development')
