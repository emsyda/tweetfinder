date_strings = [
    'last year',
    'a few months ago',
    'a few weeks ago',
    'today',
    'next christmas',
    'last August'
]

def test_dateparser():
    from dateparser import parse
    for s in date_strings:
        print(s, parse(s))
        #print('///////////////////////////////////')

