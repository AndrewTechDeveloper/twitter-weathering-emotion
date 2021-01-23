# coding: UTF-8

import csv
import datetime
import json
import os
import time

import pandas as pd
from janome.tokenizer import Tokenizer
from requests_oauthlib import OAuth1Session

t = Tokenizer()
now = datetime.datetime.now()

CONSUMER_KEY = os.getenv("CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("CONSUMER_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")


class TwitterApi:
    def __init__(self, search_word):
        self.twitter_api = OAuth1Session(
            CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_SECRET
        )
        self.url = "https://api.twitter.com/1.1/search/tweets.json?tweet_mode=extended"
        self.params = {
            "q": search_word,
            "count": 100,
            "result_type": "recent",
            "exclude": "retweets",
            "lang": "ja",
        }
        self.tweet_num = 100

    def get_next_tweets(self):
        req = self.twitter_api.get(self.url, params=self.params)
        if req.status_code == 200:
            self.x_rate_limit_remaining = req.headers["X-Rate-Limit-Remaining"]
            self.x_rate_limit_reset = req.headers["X-Rate-Limit-Reset"]
            self.tweets = json.loads(req.text)
            self.tweet_num = len(self.tweets["statuses"])
            if self.tweet_num == 0:
                return True
            self.max_id = self.tweets["statuses"][0]["id"]
            self.min_id = self.tweets["statuses"][-1]["id"]
            next_max_id = self.min_id - 1
            self.params["max_id"] = next_max_id
            return True
        else:
            return False

    def create_tweets_df(self, limit):
        tweets_df = pd.DataFrame([])
        while self.tweet_num > 0:
            ret = self.get_next_tweets()
            time.sleep(1)
            if self.tweet_num == 0 or len(tweets_df.index) > limit:
                break
            if ret:
                df = pd.json_normalize(self.tweets["statuses"])
                tweets_df = pd.concat([tweets_df, df], sort=False)
                print("アクセス可能回数:", self.x_rate_limit_remaining)
                print("リセット時間:", self.x_rate_limit_reset)
        return tweets_df

    def create_token_df(self, df):
        df.drop_duplicates(subset="user.id")
        token_list = []
        for _, row in df.iterrows():
            for token in t.tokenize(str(row["full_text"])):
                surf = token.surface
                read = token.reading
                pos = token.part_of_speech
                if (
                    read != "*"
                    and all(x not in surf for x in ("する", "なる", "なっ", "ある", "ない", "やっ"))
                    and all(
                        x not in pos
                        for x in (
                            "助動詞",
                            "感動詞",
                            "記号",
                            "助詞",
                            "非自立",
                            "接頭詞",
                            "連体詞",
                            "フィラー",
                            "代名詞",
                            "接尾",
                            "数",
                        )
                    )
                ):
                    token_list.append([surf, read, pos])
        token_df = pd.DataFrame(token_list, columns=["surf", "read", "pos"])
        return token_df


if __name__ == "__main__":
    twitter_api = TwitterApi("#ファッション")
    tweets_df = twitter_api.create_tweets_df(10000)
    token_df = twitter_api.create_token_df(tweets_df)
    tweets_df.to_csv("./tweets.csv")
    token_df.to_csv("./tokens.csv")
