# coding: UTF-8

from requests_oauthlib import OAuth1Session
from janome.tokenizer import Tokenizer
from wordcloud import WordCloud
import time
import datetime
import json
import pandas as pd
import os
import csv
import math
import twitter

t = Tokenizer()
now = datetime.datetime.now(timezone('Asia/Tokyo'))

CONSUMER_KEY = os.getenv("CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("CONSUMER_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")

class TwitterApi:
    def __init__(self, search_word):
        self.twitter_api = OAuth1Session(CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_SECRET)
        self.url = 'https://api.twitter.com/1.1/search/tweets.json?tweet_mode=extended'
        self.params = {'q': search_word, 'count': 100, 'result_type': 'recent', 'exclude': 'retweets', 'lang': 'ja'}
        self.tweet_num = 100

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

    def create_tweets_df(self, limit):
        tweets_df = pd.DataFrame([])
        while self.tweet_num > 0:
            ret = self.get_next_tweets()
            time.sleep(5)
            if self.tweet_num == 0 or len(tweets_df.index) > limit:
                break
            if ret:
                df = pd.json_normalize(self.tweets['statuses'])
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
                if read!= '*' and all(x not in surf for x in ('する', 'なる', 'なっ', 'ある', 'ない', 'やっ')) and all(x not in pos for x in ('助動詞', '感動詞', '記号', '助詞', '非自立', '接頭詞', '連体詞', 'フィラー', '代名詞', '接尾', "数")):
                    token_list.append([surf, read, pos])
        token_df = pd.DataFrame(token_list, columns=['surf', 'read', 'pos'])
        return token_df

def create_word_cloud(df):
    text = ' '.join(df['surf'])
    wordcloud = WordCloud(background_color="white",
        font_path="./SawarabiMincho-Regular.ttf",
        width=800,height=600).generate(text)
    wordcloud.to_file("./wordcloud.png")

def compare_match_of_dataframes(df1, df2):
    df1 = df1.groupby(['surf', 'read', 'pos'])['surf'].agg('count').to_frame('count')
    df2 = df2.groupby(['surf', 'read', 'pos'])['surf'].agg('count').to_frame('count')
    df1['count'] = df1['count']/df1['count'].sum()
    df2['count'] = df2['count']/df2['count'].sum()
    df = df1 * df2
    df = df[df['count'].notna()].sort_values('count', ascending=False)
    sum_of_count = df['count'].sum()
    return sum_of_count

def remove_extreme_value(df):
    q3 = df['count'].quantile(.99)
    df = df[df['count'] < q3]
    return df

def create_token_by_word(word):
    twitter_api = TwitterApi(word)
    tweets_df = twitter_api.create_tweets_df(1000)
    token_df = twitter_api.create_token_df(tweets_df)
    return token_df

def create_positive_token():
    df = pd.DataFrame([])
    df_origin_words = pd.read_csv('./positive_words.csv')
    for index, row in df_origin_words.iterrows():
        twitter_api = TwitterApi(row['word'])
        tweets_df = twitter_api.create_tweets_df(100)
        token_df = twitter_api.create_token_df(tweets_df)
        df = pd.concat([df, token_df], sort=False)
    return df

def create_negative_token():
    df = pd.DataFrame([])
    df_origin_words = pd.read_csv('./negative_words.csv')
    for index, row in df_origin_words.iterrows():
        twitter_api = TwitterApi(row['word'])
        tweets_df = twitter_api.create_tweets_df(100)
        token_df = twitter_api.create_token_df(tweets_df)
        df = pd.concat([df, token_df], sort=False)
    return df

def post_tweet(positive_rate, negative_rate):
    auth = twitter.OAuth(consumer_key=CONSUMER_KEY, consumer_secret=CONSUMER_SECRET, token=ACCESS_TOKEN, token_secret=ACCESS_SECRET)
    t = twitter.Twitter(auth=auth)
    if positive_rate < 30:
        msg = '人を傷つける言葉が大変多く使われているようです。何気なく発した言葉でも他人の人生を変えてしまうこともあります。優しい言葉を使うよう心がけましょう。'
    elif positive_rate < 40:
        msg = '人を傷つける言葉が多く使われているようです。画面の先にはリアルな人がいることを忘れないようにしましょう。'
    elif positive_rate < 50:
        msg = '人を傷つける言葉が増えてきているようです。相手を思いやった言葉遣いを心がけましょう。'
    elif positive_rate < 60:
        msg = 'ポジティブな言葉が増えてきているようです。この調子で相手をリスペクトした言葉遣いを心がけましょう！'
    elif positive_rate < 70:
        msg = 'ポジティブな言葉が大変多く増えてきているようです！あなたの言葉で救われた誰かがいるかもしれません。'
    else:
        msg = 'とても多くのポジティブな言葉が使われているようです！大変素晴らしいことです！'
    status = msg + '\n\nポジティブ度: ' + str(positive_rate) + '\nネガティブ度: ' + str(negative_rate)
    pic="./wordcloud.png"
    with open(pic,"rb") as image_file:
        image_data=image_file.read()
    pic_upload = twitter.Twitter(domain='upload.twitter.com',auth=auth)
    img = pic_upload.media.upload(media=image_data)["media_id_string"]
    t.statuses.update(status=status,media_ids=",".join([img]))

def cron_worker():
    positive_df = pd.DataFrame([])
    negative_df = pd.DataFrame([])
    random_df = pd.DataFrame([])
    while True:
        positive_df = pd.concat([positive_df, create_positive_token()], sort=False)
        negative_df = pd.concat([negative_df, create_negative_token()], sort=False)
        random_df = pd.concat([random_df, create_token_by_word('　')], sort=False)
        post_time = datetime.time(20, 0, 0).hour
        now = datetime.datetime.now().time().hour
        if now >= post_time:
            break
        else:
            break
            time.sleep(60*20)
    create_word_cloud(negative_df)

    positive_match = compare_match_of_dataframes(positive_df, random_df)
    negative_match = compare_match_of_dataframes(negative_df, random_df)
    total_match = positive_match + negative_match

    positive_rate = positive_match/total_match*100
    negative_rate = negative_match/total_match*100

    post_tweet(positive_rate, negative_rate)

cron_worker()
