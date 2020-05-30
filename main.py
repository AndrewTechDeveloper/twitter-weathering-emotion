from requests_oauthlib import OAuth1Session
from dotenv import load_dotenv
from pathlib import Path
from random import randrange
from scipy import stats
from janome.tokenizer import Tokenizer
from wordcloud import WordCloud
import time
import datetime
import json
import pandas as pd
import os
import csv
import math

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
        self.params = {'q': search_word, 'count': count, 'result_type': 'recent', 'exclude': 'retweets', 'lang': 'ja'}
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

    def create_tweets_df(self):
        tweets_df = pd.DataFrame([])
        while self.tweet_num > 0:
            ret = self.get_next_tweets()
            if self.tweet_num == 0 or len(tweets_df.index) > 10:
                break
            if ret:
                df = pd.io.json.json_normalize(self.tweets['statuses'])
                tweets_df = pd.concat([tweets_df, df], sort=False)
                print('アクセス可能回数:', self.x_rate_limit_remaining)
                print('リセット時間:', self.x_rate_limit_reset)
        return tweets_df

    def create_token_df(self, df):
        df.drop_duplicates(subset="user.id")
        token_list = []
        for index, row in df.iterrows():
            for token in t.tokenize(str(row['full_text'])):
                surf = token.surface
                read = token.reading
                pos = token.part_of_speech
                if read!= '*' and all(x not in pos for x in ('助動詞', '感動詞', '記号', '助詞', '非自立', '接頭詞', '連体詞', 'フィラー', '代名詞', '接尾')):
                    token_list.append([surf, read, pos])
        return pd.DataFrame(token_list, columns=['surf', 'read', 'pos'])

def create_word_cloud(df):
    text = ' '.join(df['surf'])
    wordcloud = WordCloud(background_color="white",
        font_path="./SawarabiMincho-Regular.ttf",
        width=800,height=600).generate(text)
    wordcloud.to_file("./wordcloud_sample.png")

def compare_dataframes(df1, df2):
    df = pd.concat([df1, df2]).duplicated(subset='surf', keep='first')

def scoring_words(df):
    score_df = df.groupby(['surf','read','pos']).count().rename(columns={'Unnamed: 0' :'count'}).sort_values('count', ascending=False)
    score_df['count'] = score_df['count']/score_df['count'].sum()
    return score_df

df_origin_positive_words = pd.read_csv('./positive_words.csv')
df_origin_negative_words = pd.read_csv('./negative_words.csv')

count = 100

df_n = pd.read_csv('./negative_token.csv')
df_p = pd.read_csv('./positive_token.csv')

exclude_duplicates(df_n, df_p)

# negative_score_df = scoring_words(df_negative_words)
# positive_score_df = scoring_words(df_positive_words)
#
# compare_dataframes(positive_score_df, negative_score_df)
# df_negative_words = pd.DataFrame([])
# for index, row in df_origin_negative_words.iterrows():
#     twitter_api = TwitterApi(row['word'], count)
#     tweets_df = twitter_api.create_tweets_df()
#     token_df = twitter_api.create_token_df(tweets_df)
#     df_negative_words = pd.concat([df_negative_words, token_df], sort=False)
#
# df_negative_words.to_csv('negative_token.csv')

# df_positive_words = pd.DataFrame([])
# for index, row in df_origin_positive_words.iterrows():
#     twitter_api = TwitterApi(row['word'], count)
#     tweets_df = twitter_api.create_tweets_df()
#     token_df = twitter_api.create_token_df(tweets_df)
#     df_positive_words = pd.concat([df_positive_words, token_df], sort=False)
#
# df_positive_words.to_csv('positive_token.csv')
# create_word_cloud(pd.read_csv('./positive_token.csv'))
