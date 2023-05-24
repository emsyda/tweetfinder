from scripts.llm import extract, _parse_response, _extract_chat, _extract_completion
from datetime import datetime

DATE_TODAY = datetime(2023, 5, 1)

QUERY_RESPONSE_PAIRS = [
(
'the year before the last year ESYudkowsky said something about dying with dignity',
"""
AUTHOR: ESYudkowsky
TOPIC: dying with dignity
DATE: last year
DATE_ACTUAL: (none)
DATE_EARLIEST: 2022-01-01
DATE_LATEST: 2022-12-31
IN_RESPONSE_TO: (none)
MENTIONS: (none)
WORDS: (none)
"""
),
]


def test_parse_response():
    assert _parse_response(QUERY_RESPONSE_PAIRS[0][1]) == \
        {
            'author': 'ESYudkowsky',
            'topic': 'dying with dignity',
            'alternate_phrasings': None,
            'date': 'last year',
            'date_actual': None,
            'date_earliest': '2022-01-01',
            'date_latest': '2022-12-31',
            'in_response_to': None,
            'mentions': None,
            'words': None,
        }


def test__extract():
    print('...................................')
    print('DATE_TODAY:', DATE_TODAY)
    
    for query, exp_response in QUERY_RESPONSE_PAIRS:
        print('///////////////////////////////////')
        response = _extract_completion(query, DATE_TODAY)
        #response = _extract_chat(query, DATE_TODAY)
        print(response)
        print('...................................')
        parsed = _parse_response(response)
        print(parsed)
        print('///////////////////////////////////')

