# The prompt
from datetime import datetime, timedelta

def _fmt(_datetime):
    return _datetime.strftime('%Y-%m-%d')

def rollback(date_today, days):
    return _fmt(date_today - timedelta(days=days))

def populate_dates(date_today: datetime | str):
    if isinstance(date_today, str):
        date_today = datetime.strptime(date_today, '%Y-%m-%d')
    return {
        'date_today': _fmt(date_today),
        'date_30_days_ago': rollback(date_today, 30),
        'date_90_days_ago': rollback(date_today, 90),
        'date_180_days_ago': rollback(date_today, 180),
        'four_years_ago': rollback(date_today, 365 * 4),
        'two_years_ago': rollback(date_today, 365 * 2),
        'last_year_jan_1': _fmt(datetime(date_today.year - 1, 1, 1)),
        'last_year_dec_31': _fmt(datetime(date_today.year - 1, 12, 31)),
    }


EXTRACTION_PROMPT = \
"""You are a tweet analyzer. The user gives you a query, and you must first extract relevant parts from it. Remember that the fact is that today's date is {date_today}
The relevant parts are:
AUTHOR (who wrote the tweet; if the author is user itself, then answer `me`; retweeting/liking a tweet doesn't count as them being the author; if it isn't explicitly understood whether this is the tweet's author or just someone mentioned, then put add it to MENTIONS instead)
TOPIC (what was the tweet about)
ALTERNATE_PHRASINGS (if the tweet was about a single topic, make up some alternate phrasing for it; if it has multiple topics, put the rest here; , *common separation)
DATE (when was the tweet published)
DATE_ACTUAL (the `DATE` expression converted to the actual date, if possible)
DATE_EARLIEST (if the `DATE` can't be converted to an actual date, then give the earliest possible date it could be referring to)
DATE_LATEST (if the `DATE` can't be converted to an actual date, then give the latest possible date it could be referring to)
IN_REPLY_TO (which single twitter user's tweet did the tweet reply to)
MENTIONS (which twitter users explicitly says were mentioned in the tweet, *common separation)
WORDS (what words the user explicitly says may have been present in the tweet, *common separation)
*common separation method: comma + space (", ")
Here is an example query:
```
aella_girl mentioned something about eating from the dumpster a few months ago. I think she responsed to @gakonst.
```
Here is the parts you extracted (in the form of the exact response you gave back to the user):
```
AUTHOR: aella_girl
TOPIC: eating from the dumpster
ALTERNATE_PHRASINGS: dumpster diving, waste food
DATE: a few months ago
DATE_ACTUAL: (none)
DATE_EARLIEST: {date_180_days_ago}
DATE_LATEST: {date_30_days_ago}
IN_REPLY_TO: gakonst
MENTIONS: (none)
WORDS: (none)
```
Note that MENTIONS was assigned `(none)` because the user didn't say anything about @aella_girl having mentioned anyone in her tweet, just that she responded to a tweet of @gakonst (without necessarily mentioning @gakonst in her tweet).
Also, WORDS were assigned `(none)` because the user didn't say anything about what words were present in the tweet. The user mentioned the overall topic, but not any specific words.
DATE_ACTUAL was assigned `(none)` because the user said `a few months ago`, which isn't very exact at all. However, it is reasonable to assume that it could have been anywhere between 30 and 180 days ago, so DATE_EARLIEST was assigned `{date_180_days_ago}` and DATE_LATEST was assigned `{date_30_days_ago}`.

Here are some more date conversion examples:
DATE: two months ago
DATE_ACTUAL: (none)
DATE_EARLIEST: {date_90_days_ago}
DATE_LATEST: {date_30_days_ago}

DATE: january the 2nd, 2021
DATE_ACTUAL: 2021-01-02
DATE_EARLIEST: (none)
DATE_LATEST: (none)

DATE: last year
DATE_ACTUAL: (none)
DATE_EARLIEST: {last_year_jan_1}
DATE_LATEST: {last_year_dec_31}

DATE: two to three years ago
DATE_ACTUAL: (none)
DATE_EARLIEST: {four_years_ago}
DATE_LATEST: {two_years_ago}

DATE: in 2017 or 2018
DATE_ACTUAL: (none)
DATE_EARLIEST: 2017-01-01
DATE_LATEST: 2018-31-01

Now, here is the real query:
```
{query}
```
Please extract the parts in the above specified form. Don't respond with anything else. You must answer with `(none)` for any parts that you can't extract.
"""
