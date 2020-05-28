from requests_oauthlib import OAuth1Session
from dotenv import load_dotenv
from pathlib import Path
import time
import json
import pandas as pd
import os
import csv
from janome.tokenizer import Tokenizer

load_dotenv(verbose=True)
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
t = Tokenizer()

CONSUMER_KEY = os.getenv("CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("CONSUMER_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")

class TwitterApi:
    def __init__(self, search_word, count):
        self.twitter_api = OAuth1Session(CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
        self.url = 'https://api.twitter.com/1.1/search/tweets.json?tweet_mode=extended'
        self.params = {'q': search_word, 'count': count, 'result_type': 'recent', 'exclude': 'retweets'}
        self.tweet_num = count

    def get_next_tweets(self):
        req = self.twitter_api.get(self.url, params=self.params)
        if req.status_code == 200:
            self.x_rate_limit_remaining = req.headers['X-Rate-Limit-Remaining']
            self.x_rate_limit_reset = req.headers['X-Rate-Limit-Reset']
            self.tweets = json.loads(req.text)
            self.tweet_num = len(self.tweets['statuses'])
            if self.tweet_num == 0:
                return True
            self.max_id = self.tweets['statuses'][0]['id']
            self.min_id = self.tweets['statuses'][-1]['id']
            next_max_id = self.min_id - 1
            self.params['max_id'] = next_max_id
            return True
        else:
            return False

search_word = '#世界平和'
count = 5

twitter_api = TwitterApi(search_word, count)
tweets_df = pd.DataFrame([])

# while twitter_api.tweet_num > 0:
#     ret = twitter_api.get_next_tweets()
#     if twitter_api.tweet_num == 0:
#         break
#     if ret:
#         df = pd.io.json.json_normalize(twitter_api.tweets['statuses'])
#         tweets_df = pd.concat([tweets_df, df], sort=False)
#         print('アクセス可能回数:', twitter_api.x_rate_limit_remaining, ' リセット時間:', twitter_api.x_rate_limit_reset)

ret = twitter_api.get_next_tweets()
df = pd.io.json.json_normalize(twitter_api.tweets['statuses'])

tokens_df = pd.DataFrame([])
for token in t.tokenize(str(df['full_text'])):
    surf = token.surface
    base = token.base_form
    pos = token.part_of_speech
    reading = token.reading
    tweets_df = pd.concat([tokens_df, df], sort=False)

tokens_df.to_csv("tokens.csv")
