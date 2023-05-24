# type tweet
from typing import TypedDict

class Tweet(TypedDict):
    id: str
    created_at: str
    author: str
    in_response_to: str
    text: str
    is_retweet: bool
    is_quote: bool
    is_liked: bool
    timestamp: int
