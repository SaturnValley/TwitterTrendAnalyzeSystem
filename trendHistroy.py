#Twitterの日本のトレンドを取得して保存

import csv
import time
import os
import datetime
import tweetTest
import tweepy

class Trend:
    def __init__(self, name, query, created_at):
        self.name = name
        self.query = query
        if isinstance(created_at, str):
            times = created_at.split(" ")
            ymd = times[0].split("-")  # year month day
            hms = times[1].split(":")  # hour min second
            self.created_at = datetime.datetime(year=int(ymd[0]), month=int(ymd[1]), day=int(ymd[2]), hour=int(hms[0]),
                                                minute=int(hms[1]), second=int(hms[2].split(".")[0]))
        else:
            self.created_at = datetime.datetime(year=created_at.year, month=created_at.month,
                                                day=created_at.day, hour=created_at.hour,
                                                minute=created_at.minute, second=created_at.second)

    def is_delete(self, now, limit):
        if now - self.created_at <= limit:
            return False
        else:
            return True

    def get_list(self):
        return [self.name, self.query, self.created_at]

    def set_created_at(self, created_at):
        self.created_at = created_at


os_path = os.path.dirname(os.path.abspath(__name__))
joined_path = os.path.join(os_path, '../data/trend_list')
csv_path = os.path.normpath(joined_path + ".csv")
api = tweetTest.api
limit = datetime.timedelta(days=7)
while True:
    try:
        trend_dict = {}
        if os.path.isfile(csv_path):
            with open(csv_path, "r", encoding="utf-8")as f_r:
                reader = csv.reader(f_r, delimiter=",", doublequote=True, lineterminator="\r\n", quotechar='"')
                for row in reader:
                    trend_dict[row[0]] = Trend(row[0], row[1], row[2])
        trends = api.trends_place(23424856)[0]["trends"]
        now = datetime.datetime.now()
        """
        delete_list=[]
        for key, value in trend_dict.items():
            if value.is_delete(now, limit):
                detete_list.append(key)
        for key in delete_list:
            del trend_dict[key]
        """
        trend_dict = {k: v for k, v in trend_dict.items() if not v.is_delete(now, limit)}
        keys = trend_dict.keys()
        for trend in trends:
            name = trend["name"]
            if name in keys:
                trend_dict[name].set_created_at(now)
            else:
                trend_dict[name] = Trend(name, trend["query"], now)
        with open(csv_path, "w", encoding="utf-8")as f_w:
            writer = csv.writer(f_w, lineterminator='\n')
            for trend in trend_dict.values():
                writer.writerow(trend.get_list())
        print("sleep",now)
        time.sleep(15 * 60)
    except tweepy.error.TweepError:
        time.sleep(15 * 60)
        continue
