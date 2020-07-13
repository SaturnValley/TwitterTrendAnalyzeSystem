# coding: utf-8

# 分析・可視化アプリケーション本体

import wx
import datetime
import csv
import community
import networkx as nx
import matplotlib
import numpy as np
import os
import MeCab
from sklearn.feature_extraction.text import TfidfTransformer
import collections
import wordDetection
from sklearn.feature_extraction.text import CountVectorizer
from urllib.parse import urlparse
import webbrowser
import wx.lib.scrolledpanel
from matplotlib import rcParams

rcParams['font.family'] = 'sans-serif'
rcParams['font.sans-serif'] = ['IPAexGothic', 'IPAPGothic']


# ツイート１つを表すクラス
class Tweet:
    def __init__(self, tweet_id, text, created_at, retweet_count, favorite_count, user_id, screen_name, is_img=0,
                 is_html=0):
        # ツイートID
        self.tweet_id = tweet_id
        # 　ツイート本文
        self.text = text
        # リツイート数
        self.retweet_count = retweet_count
        # 　いいね数
        self.favorite_count = favorite_count
        # 　ユーザーID
        self.user_id = user_id
        # ユーザー名
        self.screen_name = screen_name
        times = created_at.split(" ")
        ymd = times[0].split("-")  # year month day
        hms = times[1].split(":")  # hour min second
        self.created_at = datetime.datetime(year=int(ymd[0]), month=int(ymd[1]), day=int(ymd[2]), hour=int(hms[0]),
                                            minute=int(hms[1]), second=int(hms[2])) + datetime.timedelta(hours=9,
                                                                                                         minutes=0,
                                                                                                         seconds=0)
        # ツイートについている画像の数
        self.is_img = is_img
        # ツイートについているURLの数
        self.is_html = is_html

    # 　ツイートの内容が一致しているかを見るため
    def get09text(self, text_len):
        if len(self.text) >= text_len:
            tex = self.text[0:text_len - 1]
        else:
            tex = self.text[0:len(self.text) - 1]
        return tex


# 各種辞書作成，ツイート辞書，リツイートしたユーザーの辞書など
def create_dicts(text_len, path):
    with open("{}.csv".format(path), "r", encoding="utf-8")as f:
        reader = csv.reader(f, delimiter=",", doublequote=True, lineterminator="\r\n", quotechar='"')
        second = False
        # 　CSVの１行目を読み取り，項目のインデックス付け
        index_dict = {}  # 'tweet_id', 'text', 'created_at', 'retweet_count', 'favorite_count',user_id,screen_name,is_img","is_html"
        # リツイートしたユーザとリツイート元のツイートを対応付け
        retweeter_dict = {}  # text:set([user_id,user_id])
        # 　ツイートidとそのidのTweetオブジェクトを対応付け
        tweet_dict = {}  # id:Tweetクラスのオブジェクト
        for row in reader:
            if second:
                text = remove_urls(row[index_dict["text"]])
                if len(text) > 4 and text[0:4] == "RT @":  # RTの判定
                    try:
                        retweeted_tweet_text = text.split(":")[1][1:]
                        if len(retweeted_tweet_text) >= text_len:
                            retweeted_tweet_text = retweeted_tweet_text[0:text_len - 1]
                        else:
                            retweeted_tweet_text = retweeted_tweet_text[0:len(retweeted_tweet_text) - 1]
                        if retweeted_tweet_text not in retweeter_dict.keys():  # 辞書に未登録
                            retweeter_dict[retweeted_tweet_text] = set([int(row[index_dict["user_id"]])])
                        else:
                            retweeter_dict[retweeted_tweet_text].add(int(row[index_dict["user_id"]]))
                    except IndexError:
                        print("create_retweet_dict_error ")
                        print(text)
                else:  # RTじゃない
                    try:
                        tweet_dict[row[index_dict["tweet_id"]]] = Tweet(int(row[index_dict["tweet_id"]]), text,
                                                                        row[index_dict["created_at"]],
                                                                        int(row[index_dict["retweet_count"]]),
                                                                        int(row[index_dict["favorite_count"]]),
                                                                        int(row[index_dict["user_id"]]),
                                                                        row[index_dict["screen_name"]],
                                                                        int(row[index_dict["is_img"]]),
                                                                        int(row[index_dict["is_html"]]))
                    except ValueError:
                        continue
                    except KeyError:  # 過去に取ったデータでis_htmlとかない奴
                        tweet_dict[row[index_dict["tweet_id"]]] = Tweet(int(row[index_dict["tweet_id"]]), text,
                                                                        row[index_dict["created_at"]],
                                                                        int(row[index_dict["retweet_count"]]),
                                                                        int(row[index_dict["favorite_count"]]),
                                                                        int(row[index_dict["user_id"]]),
                                                                        row[index_dict["screen_name"]])
            else:
                # CSVの最初の１行を読み出して，項目をインデックス付け
                second = True
                count = 0
                print(row)
                for index in row:
                    index_dict[index] = count
                    count += 1
                print(index_dict)
    return index_dict, retweeter_dict, tweet_dict


# ツイートとリツイートしたユーザーを対応付けてファイル出力，後で使いまわせるように
def create_tweet_retweeter_dict(tweet_dict, retweeter_dict, text_len, path):
    # {tweet_id:{user_id,user_id}}
    # t_rtをcsvに保存する
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)
    #
    csv_path = os.path.normpath(os.path.join(path, "tweet_retweet.csv"))
    time_path = os.path.normpath(os.path.join(path, "time.csv"))
    print("csv_path t_rt", csv_path)

    # time_pathのファイルはデータを取得した日時を保存したもの，すでにある場合はそれをロード
    if os.path.isfile(time_path):
        with open(time_path, "r", encoding="utf-8")as f:
            reader = csv.reader(f, delimiter=",", doublequote=True, lineterminator="\r\n", quotechar='"')
            for row in reader:
                time_str_a = row[0]
    else:
        time_str_a = datetime.datetime.now()
        with open(time_path, "w", encoding="utf-8")as f:
            writer = csv.writer(f, lineterminator='\n')
            writer.writerow([time_str_a])

    # csv_pathのファイルは途中結果保存ファイル
    if os.path.isfile(csv_path):
        with open(csv_path, "r", encoding="utf-8")as f:
            reader = csv.reader(f, delimiter=",", doublequote=True, lineterminator="\r\n", quotechar='"')
            first = True
            tweet_retweeter_dict = {}
            for row in reader:
                if first:
                    time_str_b = row[0]
                    first = False
                else:
                    tweet_retweeter_dict[row[0]] = set([int(x) for x in row][1:])
    else:
        time_str_b = "none"
    # 　途中出力ファイルがない場合は作成
    # 　データを取得した日時と，途中出力ファイルの作成に使ったデータを取得した日が違う場合は，途中出力ファイルを作り直す
    if time_str_a != time_str_b:
        tweet_retweeter_dict = {tweet_id: retweeter_set for tweet_id, tweet in tweet_dict.items() for
                                retweeter_text, retweeter_set in retweeter_dict.items()
                                if tweet.get09text(text_len) == retweeter_text}
        with open(csv_path, "w", encoding="utf-8")as f:
            writer = csv.writer(f, lineterminator='\n')
            writer.writerow([time_str_a])
            for k, v in tweet_retweeter_dict.items():
                writer.writerow([k] + list(v))
    is_retweet_tweet_id_set = set(tweet_retweeter_dict.keys())
    delete_node_list = [tweet_id for tweet_id in tweet_dict.keys() if tweet_id not in is_retweet_tweet_id_set]
    # リツイート数0のノードを削除
    print("bofore delete t_dict", len(tweet_dict))
    for tweet_id in delete_node_list:
        del tweet_dict[tweet_id]
    print("after delete t_dict", len(tweet_dict))
    print("all number of rt in t_dict", sum([len(x) for x in tweet_retweeter_dict.values()]))
    return tweet_dict, tweet_retweeter_dict


# Loivain法の結果を返す
# n_topは対象とするツイート数の下限
# starting / ending timeは時間軸の始点終点
def create_louvain_dict(tweet_dict, tweet_retweeter_dict, retweeter_limit, starting_time=0, ending_time=0,
                        n_top=1500):
    s = datetime.datetime.now()
    time_flag = True
    # 始点終点がint（時間指定なし）だったら
    if isinstance(starting_time, int) and isinstance(ending_time, int):
        time_flag = False
    # 始点のみint（指定なし）なら，データセットの一番古い時間を探す
    if isinstance(starting_time, int):
        starting_time = search_time(tweet_dict)
    # 終点のみint（指定なし）なら，データセットの一番新しい時間を探す
    if isinstance(ending_time, int):
        ending_time = search_time(tweet_dict, starting=False)
    g = nx.Graph()
    start = datetime.datetime.now()
    node_val_dic = {}

    # set_time=datetime.datetime(2018,12,1,0,0,0)
    lower_limit = retweeter_limit
    # 　無限ループを防ぐため，リツイート数の最大を計算しておく
    max_retweet_limit = max([len(x) for x in tweet_retweeter_dict.values()])
    # 　下限＜＝リツイート数＜＝上限　に含まれるツイート数がn_topを初めて超える上限を探す

    if time_flag:
        # こっちは時間指定が１つ以上ある
        while True:
            t_rt_dict = {k: v for k, v in tweet_retweeter_dict.items() if
                         retweeter_limit >= len(v) >= lower_limit and starting_time <= tweet_dict[
                             k].created_at <= ending_time}
            if len(t_rt_dict) > n_top or retweeter_limit > max_retweet_limit:
                break
            retweeter_limit += 1
    else:
        # 時間指定なし
        while True:
            t_rt_dict = {k: v for k, v in tweet_retweeter_dict.items() if retweeter_limit >= len(v) >= lower_limit}
            if len(t_rt_dict) > n_top or retweeter_limit > max_retweet_limit:
                break
            retweeter_limit += 1
    print("sakugen t_rt_dict, len", len(t_rt_dict), datetime.datetime.now() - start, retweeter_limit)
    # ツイート間のシンプソン係数の値を計算
    for count_a, (key_a, set_a) in enumerate(t_rt_dict.items()):
        len_a = len(set_a)
        for count_b, (key_b, set_b) in enumerate(t_rt_dict.items()):
            len_b = len(set_b)
            if count_a > count_b:
                if len_a > len_b:
                    value = len(set_a & set_b) / len_b
                else:
                    value = len(set_a & set_b) / len_a
                node_val_dic[key_a, key_b] = value
    # ノードとエッジの重みをグラフに追加
    for k, v in node_val_dic.items():
        g.add_edge(k[0], k[1], weight=v)
    # mid = datetime.datetime.now()
    # print("finish loop", mid - start)
    # 　Louvain法でクラスタリング
    partition = community.best_partition(g)
    # print("finish partition", datetime.datetime.now() - mid)
    print(len(t_rt_dict), datetime.datetime.now() - s)
    return partition, lower_limit


# MatPlotLibで可視化
def create_themeriver(partition, tweet_dict, axes, division_num, col, starting_time=0, ending_time=0, cluster_limit=10):
    # 　時間の始点終点がデフォルトだった場合に適切なものを探す
    if isinstance(starting_time, int):
        starting_time = search_time(tweet_dict)
    if isinstance(ending_time, int):
        ending_time = search_time(tweet_dict, starting=False)
    # 時間のラベル表示するときに，重複部分を自動でなくす
    # 開始時と終了時の 0:普通、1:年が同じ 2:年月が同じ 3:年月日が同じ
    mode = 0
    if starting_time.year == ending_time.year:
        mode = 1
        if starting_time.month == ending_time.month:
            mode = 2
            if starting_time.day == ending_time.day:
                mode = 3
    time_delta = (ending_time - starting_time) / division_num
    themeriver = 0
    time_list = []
    # division_numの数になるように時系列を分割
    for num in range(division_num + 2):
        time_list.append(starting_time + time_delta * (num - 1 / 2))
    # 要素数が多い上位cluster_limit位までのクラスタを取得
    lists_nodes = create_lists_nodes(partition, cluster_limit)
    # 各クラスタの，特定の時間に入っているツイート数を計算
    for count, list_nodes in enumerate(lists_nodes):
        array = np.array(np.zeros(division_num + 1))
        print(len(list_nodes), list(col)[count])
        # 　１つのクラスタの要素すべて
        for node in list_nodes:
            # print(tweet_dict[node].text)
            time = tweet_dict[node].created_at
            # 　特定の時間帯
            for num in range(division_num + 1):
                if time_list[num] <= time < time_list[num + 1]:
                    array[num] += 1
                    break
        if isinstance(themeriver, int):
            # 一番最初は行列
            themeriver = array
        else:
            # ２回目以降は行列を合体
            themeriver = np.row_stack((themeriver, array))
    # 時間軸のラベル
    show_x = []
    # この値飛ばしでx軸のメモリの値を表示，ラベルが重ならないように
    show_dif = int((division_num / 10))
    if show_dif == 0:
        show_dif = 1
    if mode == 0:
        show_dif += 1
    show_dif = 2

    # 時間軸のラベルの文字を作成
    for num in range(division_num + 1):
        time = (starting_time + time_delta * num)
        string = ""
        if mode == 0:
            string = str(time.year) + "/" + str(time.month) + "/" + str(time.day) + " " + str(time.hour) + ":" + str(
                time.minute).zfill(2)  # +":"+str(time.second)
        elif mode == 1:
            string = str(time.month) + "/" + str(time.day) + " " + str(time.hour) + ":" + str(
                time.minute).zfill(2)  # +":"+str(time.second)
        elif mode == 2:
            string = str(time.day) + " " + str(time.hour) + ":" + str(time.minute).zfill(2)  # +":"+str(time.second)
        elif mode == 3:
            string = str(time.hour) + ":" + str(time.minute).zfill(2)  # + ":" + str(time.second)
        if not (num % show_dif == 0):
            string = ""
        show_x.append(string)
    # グラフの表示
    axes.stackplot(range(division_num + 1), themeriver, colors=col, baseline="sym")
    axes.set_xticks(range(division_num + 1))
    axes.set_xticklabels(show_x)


# 凡例を作成
def create_legend(partition, tweet_dict, axes, name, division_num, m_path, starting_time=0, ending_time=0,
                  legend_mode=1,
                  cluster_limit=10):
    # 　時間軸の始点終点を計算
    if isinstance(starting_time, int):
        starting_time = search_time(tweet_dict)
    if isinstance(ending_time, int):
        ending_time = search_time(tweet_dict, starting=False)
    time_delta = (ending_time - starting_time) / division_num
    m = MeCab.Tagger(f"-Ochasen -d {m_path}")
    count = 0
    # 　頻出単語の上位いくつをとるか
    legend_top = 5
    time_list = []
    # 各クラスタに含まれるツイートのテキストの単語(形態素)を格納するリスト
    m_list = []
    for num in range(division_num + 2):
        time_list.append(starting_time + time_delta * (num - 1 / 2))
    lists_nodes = create_lists_nodes(partition, cluster_limit)
    # 各クラスタの凡例を抽出
    for list_nodes in lists_nodes:
        instant_list = []
        count += 1
        for node in list_nodes:
            # 1つのクラスタの凡例抽出
            if starting_time <= tweet_dict[node].created_at <= ending_time:
                # 　テキストを形態素解析して単語を抽出
                create_mecab_list(m, tweet_dict[node].text, instant_list, name)
        # 　のちの都合で，単語のリストを英文のように空白区切りの文字列にする
        m_list.append(" ".join(instant_list))

    # modeで凡例の取得法を切り替え，0でtf-idf，1でBM25，2で頻出度
    if legend_mode == 0:
        legend_list = create_tf_idf_legend(m_list, legend_top)
    elif legend_mode == 1:
        legend_list = create_BM25_legend(m_list, legend_top)
    else:
        legend_list = create_frequent_legend(m_list, legend_top)
    # 凡例として表示
    axes.legend(legend_list)  # , fontsize=14)


# コンソール上に結果表示
def print_coms(partition, tweet_dict):
    for com in set(partition.values()):
        list_nodes = [nodes for nodes in partition.keys() if partition[nodes] == com]
        print(com)
        count = 0
        for a in list_nodes:
            tweet = tweet_dict[a]
            # 　いいね数が多いものを表示
            if tweet.favorite_count > 50:
                count += 1
                print(tweet.text)
                if count > 10:
                    break


# 　mecab_listの単語の出現回数を数える
def create_mecab_dict(mecab_list):
    # [{},{},{}...]の形
    # 一つの辞書はあるクラスタにおける単語の出現回数，{単語A：回数，単語B：回数}
    dict_list = []
    for s in mecab_list:
        # 一度文字列をリストに直す，本来は2度手間
        one_list = s.split(" ")
        # 単語数をカウント
        dict_list.append(collections.Counter(one_list))
    return dict_list


# 単語の出現回数順にした凡例リストを返す
def create_frequent_legend(m_list, top):
    legend_list = []
    for m_dict in create_mecab_dict(m_list):
        # 　出現回数で降順ソート
        d = sorted(m_dict.items(), key=lambda x: x[1], reverse=True)
        lis = []
        if top > len(d):
            top = len(d)
        count = 0
        for k, v in d:
            if count >= top:
                break
            lis.append(k)
            count += 1
        legend_list.append(",".join(lis))
    return legend_list


# 特定の品詞の単語をmecab_listに格納，使いまわす
def create_mecab_list(mecab, text, mecab_list, name):
    txt = mecab.parseToNode(text)
    while txt:
        word = txt.surface.strip(name)
        word_class = txt.feature.split(",")[0]
        # 　特定の品詞の単語のみを抜き出す
        if word_class in ["名詞", "形容詞", "形容動詞", "動詞"]:
            mecab_list.append(word)
        txt = txt.next


# tf-idfとBM25の凡例を作成，BM25の引数で切り替え
def create_tf_idf_legend(m_list, top, BM25=False):
    count_vectorizer = CountVectorizer()
    ft = count_vectorizer.fit_transform(m_list)
    if BM25:
        transformer = wordDetection.BM25Transformer()
    else:
        transformer = TfidfTransformer()
    array = transformer.fit_transform(ft).toarray()
    # 値で降順ソート
    index = array.argsort(axis=1)[:, ::-1]
    feature_names = np.array(count_vectorizer.get_feature_names())
    feature_words = feature_names[index]
    legend_list = []
    for fwords in feature_words:
        if top > len(fwords):
            top = len(fwords)
        legend_list.append(",".join(fwords[0:top]))
    return legend_list


# BM25の凡例を作成
def create_BM25_legend(m_list, top):
    return create_tf_idf_legend(m_list, top, BM25=True)


# データセット内の一番新しい/古い投稿時間を探す
def search_time(tweet_dict, starting=True):
    if starting:
        return min([tweet.created_at for tweet in tweet_dict.values()])
    else:
        return max([tweet.created_at for tweet in tweet_dict.values()])


# 同じクラスタに含まれるツイートを集めて返す
# 要素数の多い順にして，cluster_limit位まで返す
def create_lists_nodes(partition, cluster_limit):
    lists_nodes = []
    # 各クラスタの要素をそれぞれリストに
    for com in set(partition.values()):
        lists_nodes.append([nodes for nodes in partition.keys() if partition[nodes] == com])
    # クラスタの要素数でソート
    sorted_list = sorted(lists_nodes, key=lambda x: len(x), reverse=True)
    if len(sorted_list) < cluster_limit:
        cluster_limit = len(sorted_list)
    print("len sorted_list, col", len(sorted_list), cluster_limit)
    # 要素数の多いクラスタをcluster_limit個返す
    return sorted_list[:cluster_limit]


# urlを削除する，形態素解析の邪魔になるので
def remove_urls(text):
    """Return a list of urls from a text string."""
    # for word in re.split('(http)|\s', text):
    for word in text.split():
        thing = urlparse(word)
        if thing.scheme:
            text = text.replace(word, "")
            text = text.strip()
    for word in text.split("http"):
        thing = urlparse("http" + word)
        if thing.scheme:
            text = text.replace("http" + word, "")
            text = text.strip()
    return text


# 一番最初，どのデータセットを使うか選ぶGUI
class NameSelectPanel(wx.Panel):
    def __init__(self, parent, text_length, rt_limit, division_num, legend_mode, cluster_limit, col, m_path):
        wx.Panel.__init__(self, parent, -1, size=(200, 130))
        os_path = os.path.dirname(os.path.abspath(__name__))
        joined_path = os.path.join(os_path, '../data/')
        file_path = os.path.normpath(joined_path)
        file_list = os.listdir(file_path)
        # データセット格納フォルダから，データセットCSVファイルの一覧を取得
        items = [x.strip(".csv") for x in file_list if x.endswith(".csv") and not x.endswith("_pre_treatment.csv")]
        self.parent = parent
        self.name = None
        self.childFrame = None
        # リツイート元を判定するのに，テキストの頭何文字を見るか
        self.text_length = text_length
        # この値以下のリツイート数のツイートは計算しない
        self.rt_limit = rt_limit
        # 時間の分割数
        self.division_num = division_num
        # 凡例のモード
        self.legend_mode = legend_mode
        # この数未満のツイート数のクラスタは除去
        self.cluster_limit = cluster_limit
        # 表示する色
        self.col = col
        # 形態素解析辞書のパス
        self.m_path = m_path
        combo = wx.ComboBox(self, choices=items)
        combo.Bind(wx.EVT_TEXT, self.on_text)
        exe_button = wx.Button(self, wx.ID_ANY, '実行')
        exe_button.Bind(wx.EVT_BUTTON, self.execute)
        # Set sizer.
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(combo, 1, wx.EXPAND | wx.ALL, 10)
        sizer.Add(exe_button, 1, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(sizer)

    def on_text(self, event):
        combo = event.GetEventObject()
        self.name = combo.GetValue()

    # 実行ボタン押したときの挙動，初期値でのクラスタリングと可視化
    def execute(self, event):
        if self.name != None:
            os_path = os.path.dirname(os.path.abspath(__name__))
            # データセットのパス
            joined_path = os.path.join(os_path, '../data/{}'.format(self.name))
            file_path = os.path.normpath(joined_path)
            start = datetime.datetime.now()
            self.childFrame = wx.Frame(self.parent, wx.ID_ANY, self.name, size=(1400, 500))
            # 各種辞書を作成
            idx_dict, rt_dict, t_dict = create_dicts(self.text_length, file_path)
            print("create_dict{}".format(datetime.datetime.now() - start))
            # ツイートをリツイートした人の辞書作成，リツイート数0のツイートは削除
            t_dict, t_rt_dict = create_tweet_retweeter_dict(t_dict, rt_dict, self.text_length, file_path)
            print("create_t_rt_dict{}".format(datetime.datetime.now() - start))
            # クラスタリング
            louvain_dict, self.rt_limit = create_louvain_dict(t_dict, t_rt_dict, self.rt_limit)
            print("create_louvain_dict{}".format(datetime.datetime.now() - start))
            root_panel = wx.Panel(self.childFrame, wx.ID_ANY)
            root_layout = wx.BoxSizer(wx.HORIZONTAL)
            frame.SetTitle(self.name)
            # 可視化部分
            panel = WxPlot(root_panel, self.name, louvain_dict, t_dict, self.division_num, self.col.values(),
                           self.cluster_limit, m_path=self.m_path)
            # GUI部分
            panel2 = GUIPanel(root_panel, panel, self.name, self.text_length, self.rt_limit, self.division_num, t_dict,
                              t_rt_dict, louvain_dict,
                              legend_mode, col, cluster_limit, self.m_path)
            root_layout.Add(panel, 0, wx.GROW | wx.ALL, )
            root_layout.Add(panel2, 0, wx.GROW | wx.ALL, )
            root_panel.SetSizer(root_layout)
            root_layout.Fit(root_panel)
            self.childFrame.Show()
            print("finish execute", (datetime.datetime.now() - start))
        else:
            # 選択していないとき
            dialog = wx.MessageDialog(self, 'トレンド名を選択してください', 'トレンド名を選択してください', style=wx.OK)
            dialog.ShowModal()
            dialog.Destroy()


# GUI部分
class GUIPanel(wx.Panel):
    def __init__(self, parent, panel, name, text_length, rt_limit, division_num, t_dict, t_rt_dict, louvain_dict,
                 legend_mode, col, cluster_limit, m_path):
        # この辺りはNamePanelと同じ
        self.name = name
        self.text_len = text_length
        self.rt_limit = rt_limit
        self.t_dict = t_dict
        self.t_rt_dict = t_rt_dict
        self.division_num = division_num
        self.louvain_dict = louvain_dict
        self.panel = panel
        self.legend_mode = legend_mode
        self.col = col
        self.cluster_limit = cluster_limit
        self.m_path = m_path
        super().__init__(parent, wx.ID_ANY)
        # 本体部分の構築，各種GUIパーツ
        root_panel = wx.Panel(self, wx.ID_ANY)
        # 時間の分割数を変えるスライダー
        self.division_slider_panel = DivisionSliderPanel(root_panel, self.division_num)
        # データセットの時間の始点終点
        self.start = search_time(t_dict)
        self.end = search_time(t_dict, starting=False)
        self.start_date_panel = DatePanel(root_panel, "始点", self.start)
        self.end_date_panel = DatePanel(root_panel, "終点", self.end)
        # 最低リツイート数
        self.retweet_limit_panel = RetweetLimitPanel(root_panel, self.rt_limit)
        # 凡例生成の方法選択
        self.legend_select_panel = LegendSelectPanel(root_panel, self.legend_mode)
        # 上記の条件変更を反映する
        self.button_panel = ButtonPanel(root_panel)
        # 実際のツイートを表示するボタン
        self.another_panel = AnotherPanel(root_panel, self.name, self.louvain_dict, list(self.col.keys()), self.t_dict)
        root_layout = wx.BoxSizer(wx.VERTICAL)
        root_layout.Add(self.division_slider_panel, 0, wx.GROW | wx.ALL, )
        root_layout.Add(self.start_date_panel, 0, wx.GROW | wx.ALL, border=10)
        root_layout.Add(self.end_date_panel, 0, wx.GROW | wx.ALL, border=10)
        root_layout.Add(self.retweet_limit_panel, 0, wx.GROW | wx.ALL, border=10)
        root_layout.Add(self.legend_select_panel, 0, wx.GROW | wx.ALL, border=10)
        root_layout.Add(self.button_panel, 0, wx.GROW | wx.ALL, border=10)
        root_layout.Add(self.another_panel, 0, wx.GROW | wx.ALL, border=10)
        root_panel.SetSizer(root_layout)
        root_layout.Fit(root_panel)
        self.button_panel.exe_button.Bind(wx.EVT_BUTTON, self.exe_button_event)
        self.button_panel.clear_button.Bind(wx.EVT_BUTTON, self.clear_button_event)

    # 実行ボタンを押したときの挙動
    def exe_button_event(self, event):
        # 入力された条件を取得
        d_num = self.division_slider_panel.slider.GetValue()
        s_date = self.start_date_panel.return_date()
        e_date = self.end_date_panel.return_date()
        rt_limit = int(self.retweet_limit_panel.text_box.GetValue())
        l_mode = self.legend_select_panel.get_value()
        zoom_mode = self.button_panel.get_value()  # 0だとzoomのみ、1はlouvain再計算
        change = False
        # 実行前と変わった条件を探す
        if rt_limit != self.rt_limit:
            self.rt_limit = rt_limit
            zoom_mode = 1
            change = True
        if d_num != self.division_num:
            print("division change")
            self.division_num = d_num
            change = True
        if s_date != self.start:
            print("start change")
            self.start = s_date
            change = True
        if e_date != self.end:
            print("end change")
            self.end = e_date
            change = True
        if l_mode != self.legend_mode and (not change):  # legendのみかえた場合はここ
            self.legend_mode = legend_mode
            create_legend(self.louvain_dict, self.t_dict, self.panel.subplot.axes, self.name,
                          division_num=self.division_num,
                          starting_time=self.start, ending_time=self.end, legend_mode=l_mode,
                          cluster_limit=len(col),
                          mecab_path=self.m_path)
            self.panel.draw()
            self.legend_mode = l_mode
        if s_date >= e_date:
            change = False
        # クラスタリングしなおす場合はここ
        if zoom_mode == 1 and change:
            print("louvain change")
            self.louvain_dict, self.rt_limit = create_louvain_dict(self.t_dict, self.t_rt_dict, self.rt_limit, s_date,
                                                                   e_date)
            self.another_panel.update_partition(self.louvain_dict)
            self.start = s_date
            self.end = e_date
            change = True
        # 条件の変更が正式なものなら変更を反映
        if (change):
            print(self.start)
            print(self.end)
            self.panel.subplot.clear()
            self.legend_mode = l_mode
            create_themeriver(self.louvain_dict, self.t_dict, self.panel.subplot.axes,
                              division_num=self.division_num, col=self.col.values(),
                              starting_time=self.start, ending_time=self.end, cluster_limit=len(self.col))
            create_legend(self.louvain_dict, self.t_dict, self.panel.subplot.axes, self.name,
                          division_num=self.division_num,
                          m_path=self.m_path,
                          starting_time=self.start, ending_time=self.end, legend_mode=l_mode,
                          cluster_limit=len(self.col))
            self.panel.draw()

    # 条件を初期化
    def clear_button_event(self, event):
        self.division_slider_panel.set_default()
        self.start_date_panel.set_default()
        self.end_date_panel.set_default()
        self.retweet_limit_panel.set_default()
        self.legend_select_panel.set_default()


# 時間軸の分割数を変えるスライダー
class DivisionSliderPanel(wx.Panel):
    def __init__(self, parent, division_num):
        super().__init__(parent, wx.ID_ANY)
        s_text = wx.StaticText(self, wx.ID_ANY, '分割数')
        self.default = division_num
        self.slider = wx.Slider(self, wx.ID_ANY, style=wx.SL_LABELS | wx.SL_AUTOTICKS, size=(300, 50))
        layout = wx.BoxSizer(wx.HORIZONTAL)
        layout.Add(s_text, flag=wx.GROW)
        layout.Add(self.slider, flag=wx.GROW)
        self.slider.SetValue(self.default)
        print("default")
        self.slider.SetTickFreq(10)
        self.slider.SetPageSize(200)
        self.slider.SetMin(5)
        self.slider.SetMax(50)
        self.SetSizer(layout)

    def set_default(self):
        self.slider.SetValue(self.default)


# 時間軸の始点終点を指定する部分
class DatePanel(wx.Panel):
    def __init__(self, parent, text, date_time):
        super().__init__(parent, wx.ID_ANY)
        self.text_box_list = []
        self.default = date_time
        label_list = ["年", "月", "日", "時", "分", "秒"]
        date_time_list = [date_time.year, date_time.month, date_time.day, date_time.hour, date_time.minute,
                          date_time.second]

        for num in range(len(label_list)):
            t = wx.TextCtrl(self, wx.ID_ANY, str(date_time_list[num]), size=(40, -1))
            t.SetMaxLength(4)
            self.text_box_list.append(t)

        layout = wx.BoxSizer(wx.HORIZONTAL)
        layout.Add(wx.StaticText(self, wx.ID_ANY, text), flag=wx.GROW)
        for num in range(len(label_list)):
            layout.Add(self.text_box_list[num], flag=wx.GROW)
            layout.Add(wx.StaticText(self, wx.ID_ANY, label_list[num]), flag=wx.GROW)
        self.SetSizer(layout)

    # テキストボックスの入力を時間に変換
    def return_date(self):
        v = []
        for text in self.text_box_list:
            v.append(int(text.GetValue()))
        return datetime.datetime(year=v[0], month=v[1], day=v[2], hour=v[3], minute=v[4], second=v[5])

    def set_default(self):
        self.text_box_list[0].SetValue(str(self.default.year))
        self.text_box_list[1].SetValue(str(self.default.month))
        self.text_box_list[2].SetValue(str(self.default.day))
        self.text_box_list[3].SetValue(str(self.default.hour))
        self.text_box_list[4].SetValue(str(self.default.minute))
        self.text_box_list[5].SetValue(str(self.default.second))


# リツイート数の下限を設定
class RetweetLimitPanel(wx.Panel):
    def __init__(self, parent, rt_limit):
        self.default = str(rt_limit)
        super().__init__(parent, wx.ID_ANY)
        self.text_box = wx.TextCtrl(self, wx.ID_ANY, self.default, size=(30, -1))
        layout = wx.BoxSizer(wx.HORIZONTAL)
        layout.Add(wx.StaticText(self, wx.ID_ANY, "最低リツイート回数"), flag=wx.GROW)
        layout.Add(self.text_box, flag=wx.GROW)
        self.SetSizer(layout)

    def set_default(self):
        self.text_box.SetValue(self.default)


# 凡例の取得法を指定するラジオボタン
class LegendSelectPanel(wx.Panel):
    def __init__(self, parent, default):
        self.default = default
        super().__init__(parent, wx.ID_ANY)
        layout = wx.BoxSizer(wx.HORIZONTAL)
        self.radiobutton_list = [wx.RadioButton(self, wx.ID_ANY, 'tf-idf', style=wx.RB_GROUP),
                                 wx.RadioButton(self, wx.ID_ANY, 'BM25'),
                                 wx.RadioButton(self, wx.ID_ANY, '頻出度')]
        layout.Add(wx.StaticText(self, wx.ID_ANY, "凡例抽出法    "), flag=wx.GROW)
        for radiobutton in self.radiobutton_list:
            layout.Add(radiobutton, flag=wx.GROW)
        self.SetSizer(layout)

    def set_default(self):
        self.radiobutton_list[self.default].SetValue(True)

    def get_value(self):
        for num in range(len(self.radiobutton_list)):
            if self.radiobutton_list[num].GetValue():
                return num


# 実行やクリア，ズームかクラスタリングしなおすかのボタン
class ButtonPanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent, wx.ID_ANY)
        self.exe_button = wx.Button(self, wx.ID_ANY, '実行')
        self.clear_button = wx.Button(self, wx.ID_ANY, 'クリア')
        self.radiobutton_list = [
            wx.RadioButton(self, wx.ID_ANY, 'ズームのみ', style=wx.RB_GROUP),
            wx.RadioButton(self, wx.ID_ANY, '再計算')]
        layout = wx.BoxSizer(wx.HORIZONTAL)
        layout.Add(self.exe_button, flag=wx.GROW)
        layout.Add(self.clear_button, flag=wx.GROW)
        for button in self.radiobutton_list:
            layout.Add(button, flag=wx.GROW)
        self.SetSizer(layout)

    def get_value(self):
        for num in range(len(self.radiobutton_list)):
            if self.radiobutton_list[num].GetValue():
                return num


# 実際のツイートを表示するボタン，新しいウィンドウで開く
class AnotherPanel(wx.Panel):  # 複窓
    def __init__(self, parent, name, partition, col, t_dict):
        self.parent = parent
        self.partition = partition
        self.col = col
        self.name = name
        self.t_dict = t_dict
        self.childFrame = None
        #        self.is_closed=False
        wx.Panel.__init__(self, parent)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.showChildBtn = wx.Button(self, label="tweetを見る", pos=(10, 10))
        sizer.Add(self.showChildBtn)
        self.Bind(wx.EVT_BUTTON, self.show_child, self.showChildBtn)
        self.radiobutton_list = [wx.RadioButton(self, wx.ID_ANY, '投稿時間順', style=wx.RB_GROUP),
                                 wx.RadioButton(self, wx.ID_ANY, 'いいね順'),
                                 wx.RadioButton(self, wx.ID_ANY, '画像数順')]
        for radiobutton in self.radiobutton_list:
            sizer.Add(radiobutton, flag=wx.GROW)
        self.SetSizer(sizer)

    def show_child(self, event):
        self.childFrame = wx.Frame(self.parent, wx.ID_ANY, "ツイートの詳細")
        # 新しいウィンドウで開く
        tabpanel = TabPanel(self.childFrame, self.partition, self.col, self.name, self.t_dict,
                            cluster_limit=len(self.col),
                            mode=self.get_value())
        self.childFrame.Show()

    def update_partition(self, partition):
        self.partition = partition

    def get_value(self):
        for num in range(len(self.radiobutton_list)):
            if self.radiobutton_list[num].GetValue():
                return num


# 実際のツイート表示，画像を取り扱うところ
class ImagePanel(wx.Panel):  # 画像
    def __init__(self, parent, img_dir_path, panel_size=150):
        wx.Panel.__init__(self, parent)
        sizer = wx.FlexGridSizer(rows=2, cols=2, gap=(0, 0))
        img_list = os.listdir(img_dir_path)
        for img in img_list:
            # print(img)
            instant_panel = wx.Panel(self, wx.ID_ANY)
            image = wx.Image(os.path.normpath(os.path.join(img_dir_path, img)))
            h = image.GetHeight()
            w = image.GetWidth()
            if (h < w):
                scale = panel_size / w
            else:
                scale = panel_size / h
            image.Rescale(w * scale, h * scale)  # ここのsizeを変更して画像の大きさ蛙
            instant_panel.SetSize(w * scale, h * scale)
            self.bitmap = image.ConvertToBitmap()
            wx.StaticBitmap(instant_panel, -1, self.bitmap, (0, 0), image.GetSize())
            sizer.Add(instant_panel, flag=wx.EXPAND | wx.ALL, border=5)
        self.SetSizer(sizer)


# 実際のツイート内の，URLをボタンとして別に設置
class URLPanel(wx.Panel):  # urlを開く
    def __init__(self, parent, html_dir_path):
        wx.Panel.__init__(self, parent)
        sizer = wx.BoxSizer(wx.VERTICAL)
        with open(html_dir_path, "r", encoding="utf-8")as f:
            reader = csv.reader(f, delimiter=",", doublequote=True, lineterminator="\r\n", quotechar='"')
            for row in reader:
                url = row[0]
                button = wx.Button(self, wx.ID_ANY, url, style=wx.BU_LEFT)
                button.Bind(wx.EVT_BUTTON, self.click_event)
                sizer.Add(button, flag=wx.EXPAND, border=5)
        self.SetSizer(sizer)

    def click_event(self, event):
        click = event.GetEventObject()  # クリックされたのはどのオブジェクトか
        click_text = click.GetLabel()  # そのオブジェクトのラベルを取得
        webbrowser.open(click_text)


# ツイートのテキスト本文
class TweetTextPanel(wx.Panel):
    def __init__(self, parent, tweet):
        wx.Panel.__init__(self, parent)
        sizer = wx.BoxSizer(wx.VERTICAL)
        for line in tweet.text.split("\n"):
            static_text = wx.StaticText(self, wx.ID_ANY, line)
            sizer.Add(static_text, flag=wx.EXPAND, border=5)
        self.SetSizer(sizer)


# ツイート1つを構成する，テキストと画像とURL
class TweetPanel(wx.Panel):  # Tweet1つ
    def __init__(self, parent, tweet, name, panel_size=200):
        wx.Panel.__init__(self, parent)
        os_path = os.path.dirname(os.path.abspath(__name__))
        joined_path = os.path.join(os_path, '../data/{}/{}'.format(name, tweet.tweet_id))
        img_dir_path = os.path.normpath(os.path.join(joined_path, "img"))
        html_dir_path = os.path.normpath(os.path.join(joined_path, "html/url.csv"))
        box = wx.StaticBox(self, wx.ID_ANY, tweet.screen_name + " " + tweet.created_at.__str__())
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        text_panel = TweetTextPanel(self, tweet)
        sizer.Add(text_panel)
        if os.path.isdir(img_dir_path):
            img_panel = ImagePanel(self, img_dir_path, panel_size=panel_size)
            sizer.Add(img_panel)
        if os.path.isfile(html_dir_path):
            url_panel = URLPanel(self, html_dir_path)
            sizer.Add(url_panel)
        self.SetSizer(sizer)


# 同じクラスタのツイート全部管理
class ClusterTweetsPanel(wx.lib.scrolledpanel.ScrolledPanel):
    def __init__(self, parent, name, tweets_list, dif=10):
        wx.lib.scrolledpanel.ScrolledPanel.__init__(self, parent)
        self.tweets_list = tweets_list
        self.index = 0
        self.dif = dif
        self.name = name
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetupScrolling()
        self.Bind(wx.EVT_SCROLLWIN, self.scrolled_bottom)
        self.create_panel()
        self.SetSizer(self.sizer)
        self.Layout()
        self.sizer.Fit(self)
        self.SetSize(parent.GetSize())

    def scrolled_bottom(self, event):
        event.Skip()
        if self.GetScrollRange(wx.VERTICAL) == self.GetScrollPos(wx.VERTICAL) + self.GetScrollPageSize(wx.VERTICAL):
            self.create_panel()
            self.sizer.Layout()
            self.SetupScrolling(scrollToTop=False)

    def create_panel(self):
        if self.index + self.dif > len(self.tweets_list):
            next_index = len(self.tweets_list)
        else:
            next_index = self.index + self.dif
        for tweet in self.tweets_list[self.index:next_index]:
            panel = TweetPanel(self, tweet, self.name)
            self.sizer.Add(panel)
        self.index = next_index

    def count_reset(self):
        self.index = 0


# 実際のツイートの，クラスタを切り替えるタブ機能
class TabPanel(wx.Panel):
    def __init__(self, parent, partition, col, name, t_dict, cluster_limit=10, mode=0):
        # colは辞書のkey()
        # modeはソートのモード、0:投稿日時順、1:いいね数、2画像数
        self.notebook = wx.Notebook(parent, wx.ID_ANY)
        lists_nodes = create_lists_nodes(partition, cluster_limit)
        for count, list_nodes in enumerate(lists_nodes):
            list_tweets = [values for keys, values in t_dict.items() if keys in list_nodes]
            if (mode == 0):
                sorted_list = sorted(list_tweets, key=lambda x: x.created_at, reverse=True)
            elif (mode == 1):
                sorted_list = sorted(list_tweets, key=lambda x: x.favorite_count, reverse=True)
            elif (mode == 2):
                sorted_list = sorted(list_tweets, key=lambda x: x.is_img, reverse=True)
            panel = ClusterTweetsPanel(self.notebook, name, sorted_list)
            panel.SetBackgroundColour(wx.WHITE)
            self.notebook.InsertPage(count, panel, col[count])


# グラフでの可視化部分
class WxPlot(wx.Panel):
    def __init__(self, parent, name, louvain_dict, t_dict, division_num, col, cluster_limit, m_path):
        from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
        from matplotlib.figure import Figure
        self.parent = parent
        self.name = name
        self.cluster_limit = cluster_limit
        self.m_path = m_path
        # グラフ部分のサイズ指定
        wx.Panel.__init__(self, parent, size=(1000, 500))
        self.figure = Figure(None)
        self.figure.set_facecolor((0.9, 0.9, 1.))
        self.subplot = self.figure.add_subplot(111)

        self.canvas = FigureCanvasWxAgg(self, -1, self.figure)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.EXPAND)
        self.SetSizer(sizer)

        # 可視化用のデータ作成
        create_themeriver(louvain_dict, t_dict, self.subplot.axes, division_num=division_num, col=col,
                          cluster_limit=len(col))
        # 凡例作成
        create_legend(louvain_dict, t_dict, self.subplot.axes, self.name, division_num=division_num,
                      cluster_limit=len(col), m_path=self.m_path)
        self.draw()

    def draw(self):
        print('draw!')
        self.canvas.draw()  # 単体で有効！


if __name__ == '__main__':
    # カスタムフレームを初期化してアプリケーションを開始
    matplotlib.interactive(True)
    matplotlib.use('WXAgg')
    app = wx.App()

    text_length = 10
    rt_limit = 10  # この値以下のリツイート数のツイートは計算しない
    division_num = 10  # 時間の分割数
    legend_mode = 1
    cluster_limit = 10  # この数未満のツイート数のクラスタは除去
    col = {"赤": "#FF0000", "黄": "#FFFF00", "水色": "#00FFFF", "ピンク": "#FFC0CB", "黄緑": "#00FF00", "青": "#0000FF",
           "紫": "#800080", "銀": "#C0C0C0", "緑": "#008000", "橙": "#FFA500"}
    mecab_path = "C:\\Users\\admin\\Desktop\\dic\\mecab-ipadic-neologd"
    frame = wx.Frame(None, size=(200, 200))
    panel = NameSelectPanel(frame, text_length, rt_limit, division_num, legend_mode, cluster_limit, col, mecab_path)
    frame.Show()
    app.MainLoop()
