from scripts.prompts import EXTRACTION_PROMPT, populate_dates

import openai
import re
from datetime import datetime, timedelta


def info_template():
    fields = 'AUTHOR TOPIC ALTERNATE_PHRASINGS DATE DATE_ACTUAL DATE_EARLIEST DATE_LATEST IN_REPLY_TO MENTIONS WORDS'
    return {field.lower(): None for field in fields.split()}


def _extract_completion(query: str, date_today: str):
    res = openai.Completion.create(
        engine='text-davinci-003',
        prompt=EXTRACTION_PROMPT.format(query=query, **populate_dates(date_today)),
        temperature=0.2,
        max_tokens=100,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None#['\n'],
    )
    return res['choices'][0]['text'].strip()


def _extract_chat(query: str, date_today: str):
    res = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=[{
            'role': 'user',
            'content': EXTRACTION_PROMPT.format(query=query, **populate_dates(date_today)),
        }],
        temperature=0.2,
        max_tokens=100,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None#['\n'],
    )
    return res['choices'][0]['message']['content'].strip()


def _parse_response(res):
    # for each field exctract the part that comes after '<field>: '
    extracted = info_template()
    for f in info_template():
        match = re.search(f'{f.upper()}: (.*)', res)
        value = match and match.group(1)
        if value and value != '(none)':
            extracted[f] = value
    return extracted


def extract_info(query: str, date_today: str):
    # text-davinci-003 (Completion) often does better, especially the ALTERNATE_PHRASINGS field,
    #  which gpt-3.5-turbo (Chat) often omits, nor does it seem to be any faster 
    #  (although gpt-4 Chat does it as well/better as davinci, but is slower and more expensive)
    # However, gpt-3.5-turbo (Chat) is considerably better at mapping the date expression to actual date
    return _parse_response(_extract_chat(query, date_today))


def modify_filters(filters, info):
    """`info` is the result of `extract(query)`"""
    # to milliseconds
    to_ms = lambda s: int(datetime.strptime(s, '%Y-%m-%d').timestamp() * 1000)
    split_comma = lambda s: re.split(r',\s*', s)

    filters = filters.copy() if filters else {}

    for k in ['author', 'in_reply_to']:
        if info[k] and not filters.get(k):
            filters[k] = info[k]
    
    if info['date_actual']:
        if not filters.get('before'):
            filters['before'] = to_ms(info['date_actual']) + 86400 * 1000
        if not filters.get('after'):
            filters['after'] = to_ms(info['date_actual']) - 86400 * 1000
    
    if info['date_earliest']:
        if not filters.get('after'):
            filters['after'] = to_ms(info['date_earliest'])
    
    if info['date_latest']:
        if not filters.get('before'):
            filters['before'] = to_ms(info['date_latest']) + 86400 * 1000
    
    if info['words']:
        # comment this out because "topic" always gives k-nearest, matching or not
        # if "words" filter it present it adds a nice additional pre-filter
        #if info['topic']:
        #    # k-nearest algo will prefer those tweets in any case if it contains that word
        #    words = [x for x in split_comma(info['words'].lower()) if x not in info['topic'].lower()]
        #    filters['words'] = ', '.join(words)
        #else:
        filters['words'] = info['words']
    
    if info['mentions']:
        if filters.get('in_reply_to'):
            deduct = split_comma(filters['in_reply_to'].lower())
            mentions = ([x for x in split_comma(info['mentions']) if x.lower() not in deduct])
            filters['mentions'] = ', '.join(mentions)
        else:
            filters['mentions'] = info['mentions']
    
    if info['topic']:
        # just for retrieving their positions (for highlighting in the UI)
        filters['optional_words'] = ', '.join(info['topic'].split())

    return {k : v for k, v in filters.items() if v}
    


"""
ChatCompletion.create() response:
{
  "choices": [
    {
      "finish_reason": "stop",
      "index": 0,
      "message": {
        "content": "AUTHOR: ESYudkowsky\nTOPIC: dying with dignity\nALTERNATE_PHRASINGS: (none)\nDATE: last year\nIN_REPLY_TO: (none)\nMENTIONS: (none)\nWORDS: (none)",
        "role": "assistant"
      }
    }
  ],
  "created": 1684184706,
  "id": "chatcmpl-7GZfOhRIKI8RzYwglNdftCOLTwGbq",
  "model": "gpt-3.5-turbo-0301",
  "object": "chat.completion",
  "usage": {
    "completion_tokens": 51,
    "prompt_tokens": 437,
    "total_tokens": 488
  }
}
"""