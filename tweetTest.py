# coding:utf-8

import tweepy

CONSUMER_KEY="カスタマーキー"
CONSUMER_SECRET="カスタマーキーシークレット"
auth=tweepy.OAuthHandler(CONSUMER_KEY,CONSUMER_SECRET)
ACCESS_TOKEN="アクセストークン"
ACCESS_SECRET="アクセストークンシークレット"
auth.set_access_token(ACCESS_TOKEN,ACCESS_SECRET)

api=tweepy.API(auth,wait_on_rate_limit=True)
#自動で上限に達すると待ってくれるらしい
print("DONE")
