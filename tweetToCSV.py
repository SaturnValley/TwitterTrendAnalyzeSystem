# coding: utf-8

#trend_listに含まれる文字やクエリを読み込んで，ツイートを取得


import tweetTest
import csv
import tweepy
import os
import urllib

api = tweetTest.api
os_path = os.path.dirname(os.path.abspath(__name__))
trend_list_path = os.path.normpath(os.path.join(os_path, '../data/trend_list.csv'))
with open(trend_list_path, "r", encoding="utf-8")as f:
    trend_list = []
    reader = csv.reader(f, delimiter=",", doublequote=True, lineterminator="\r\n", quotechar='"')
    for row in reader:
        trend_list.append([row[0], row[1], row[2]])
count = 0
for t in trend_list:
    print("{}:{},{}".format(count, t[2], t[0]))
    count += 1

x = -1
while (x < 0 or x > count):
    x2 = input("input num:")
    x = int(x2)

#nameやqueryを後で変更すれば，普通のテキスト検索も可能

name = trend_list[x][0]
query = trend_list[x][1]
time=trend_list[x][2]

joined_path = os.path.join(os_path, '../data/{}'.format(name))
pre_treatment_csv_path = os.path.normpath(joined_path + "_pre_treatment" + ".csv")
csv_path = os.path.normpath(joined_path + ".csv")
print(name)
print(query)
tweets = api.search(q=query, count=100, tweet_mode="extended")

latest_tweet_id = -1
if os.path.isfile(csv_path):
    second = False
    index_dict = {}
    with open(csv_path, "r", encoding="utf-8")as f:
        reader = csv.reader(f, delimiter=",", doublequote=True, lineterminator="\r\n", quotechar='"')
        for row in reader:
            if (second):
                if (latest_tweet_id < int(row[index_dict["tweet_id"]])):
                    latest_tweet_id = int(row[index_dict["tweet_id"]])
            else:
                second = True
                count = 0
                print(row)
                for index in row:
                    index_dict[index] = count
                    count += 1
                print(index_dict)

error_count = 0
query_count = 0
unicode_error_count = 0
finish_flag = False

os.makedirs(os.path.normpath(joined_path), exist_ok=True)
with open(os.path.normpath(os.path.join(joined_path, "time.csv")), "a", encoding="utf-8")as f:
    writer = csv.writer(f, lineterminator='\n')
    writer.writerow([time])

with open(pre_treatment_csv_path, "a", encoding="utf-8")as f:
    writer = csv.writer(f, lineterminator='\n')
    lis = ["tweet_id", "text", "created_at", "retweet_count", "favorite_count", "user_id", "screen_name", "is_img",
           "is_html"]
    # is_img, is_htmlは画像やhtmlあると1以上，ないと0
    if not os.path.isfile(csv_path):
        writer.writerow(lis)
    while len(tweets) > 0:
        query_count += 1
        now_max_id = tweets[-1].id
        print(query_count)
        for tweet in tweets:
            if (latest_tweet_id > 0 and tweet.id <= latest_tweet_id):
                finish_flag = True
                break
            path = os.path.join(joined_path, tweet.id_str)
            img_count = 0
            html_count = 0
            if len(tweet.full_text) > 4 and tweet.full_text[0:4] != "RT @":  # RTじゃなければ画像とか保存
                if hasattr(tweet, "extended_entities"):
                    # print(statutweets.extended_entities)
                    img_path = os.path.join(path, "img")
                    os.makedirs(os.path.normpath(img_path), exist_ok=True)
                    for a in tweet.extended_entities["media"]:
                        try:
                            img = urllib.request.urlopen(a['media_url'])
                            localfile = open(
                                os.path.join(img_path, "{}.{}".format(img_count, a["media_url"].split(".")[-1])), 'wb')
                            localfile.write(img.read())
                            img.close()
                            localfile.close()
                            img_count += 1
                        except:
                            print("b")
                            continue

                if len(tweet.entities["urls"]) != 0:
                    html_path = os.path.normpath(os.path.join(path, "html"))
                    os.makedirs(html_path, exist_ok=True)
                    for a in tweet.entities["urls"]:
                        try:
                            with open(os.path.join(html_path, "url.csv"), "a", encoding="utf-8")as url_file:
                                url_writer = csv.writer(url_file, lineterminator='\n')
                                url_writer.writerow([a["expanded_url"]])
                            html_count += 1
                        except urllib.error.HTTPError:
                            print("HTTP ERROR")
                            continue
                        except urllib.error.URLError:
                            print("URL ERROR")
                            continue
                        except:
                            print("ERROR")
                            continue


            l = [tweet.id, tweet.full_text, tweet.created_at, tweet.retweet_count, tweet.favorite_count,
                 tweet.user.id, tweet.user.screen_name, img_count, html_count]
            writer.writerow(l)
        if (finish_flag):
            break
        while True:
            try:
                tweets = api.search(q=query, count=100, max_id=now_max_id - 1, tweet_mode="extended")
                break
            except(ConnectionResetError):
                print("ConnectionResetError")
                time.sleep(60)
            except(tweepy.error.TweepError):
                print("tweepy.error.TweepError")
                error_count += 1
                if (error_count > 100):
                    break
                continue


#取得したツイートがおかしい場合に，整形する（変な改行あった場合など）
with open(csv_path, "a", encoding="utf-8")as f:
    with open(pre_treatment_csv_path, "r", encoding="utf-8")as f2:
        writer = csv.writer(f, lineterminator='\n')
        reader = csv.reader(f2, delimiter=",", doublequote=True, lineterminator="\r\n", quotechar='"')
        first = True
        pre_row = []  # 途中で変な改行あったときのため
        for row in reader:
            if (first):
                first = False
                writer.writerow(row)
                index_len = len(row)
            else:
                if (len(row) != index_len):
                    if (pre_row == []):
                        pre_row = row
                    else:
                        for a in range(len(row)):
                            if (a == 0):
                                pre_row[len(pre_row) - 1] += row[a]
                            else:
                                pre_row.append(row[a])
                        if (len(pre_row) == index_len):
                            row = pre_row
                            writer.writerow(row)
                            pre_row = []
                else:
                    writer.writerow(row)

with open(csv_path, "r", encoding="utf-8")as f2:
    reader = csv.reader(f2, delimiter=",", doublequote=True, lineterminator="\r\n", quotechar='"')
    first = True
    correct = True
    for row in reader:
        if (first):
            first = False
            index_len = len(row)
        else:
            if (index_len != len(row)):
                print("dame")
                correct = False
                break
    if correct:
        os.remove(pre_treatment_csv_path)
print("END")
print("error_count={}".format(error_count))
print("unicode_error_count={}".format(unicode_error_count))
