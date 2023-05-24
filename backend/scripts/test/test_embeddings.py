from scripts.embeddings import main
import os

from dotenv import load_dotenv
load_dotenv('.env.local')

import sys

base_args = [
    sys.argv[0],
    'paulfchristiano',
    '--test',
]

def test_generate_embeddings():
    sys.argv = base_args
    main()

def test_query():
    sys.argv = base_args + [
    '--query=place where you can trade cryptocurrency',
    '-k', '4'
    ]
    main()