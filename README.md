# TwitterTrendAnalyzeSystem
自著の論文[Time-series Visualization of Twitter Trends](https://www.scitepress.org/Link.aspx?doi=10.5220/0008964802010208)で使った対話的Twitterの分析・可視化システムです．  

このプログラム群は，以下のような内容です．  
実際に使用する場合は以下の順で実行してください．  
tweetTest.py（TwitterAPIを使用するための初期設定）
↓
trendHistory.py（ツイッタートレンドを取得）
↓
tweetToCSV.py（トレンドに関連するツイートを取得）
↓
retweetClustering_GUI_img_html.py（分析可視化）
また，Pythonのほかに形態素解析器MeCabと辞書のインストールが必要です．  

## 1.retweetClustering_GUI_img_html.py
  分析・可視化システムの本体  
  収集したツイートを保存したCSVファイルを分析する  
  分析手法は[RetweetClustering](https://dl.acm.org/doi/10.1145/3106426.3106451)をもとにしており，可視化手法はThemeRiverを使用  
  分析の途中結果を"../data/（トレンド名:変数nameに相当）/tweet_retweet.csv" に保存する．
  ### GUIの説明  
  ### * 分割数
    横軸（時間軸）の分割数を変更する．初期値は10，5~50範囲で変更可能．  
  ### * 始点，終点
    横軸（時間軸）の両端を変更する．初期値は対象ツイートの内，一番新しい/古いツイートの投稿時間  
  ### * 最低リツイート回数
    リツイート（RT）回数を用いて，分析対象とするツイートの条件を変更する．  
    対話的システムとして処理の待ち時間を減らすため，以下の2つの条件を満たすツイートを分析対象のツイートとして選んでいる．  
    始点　≦　対象とするツイートの投稿時間　≦　終点    
    最低RT数 ≦ 対象とするツイートのRT数 ≦ 最大RT数  
    この最大RT数は，対象となるツイート数が1500を超える最適な数に自動設定される．  
  ### * 凡例抽出方法
    グラフの凡例を抽出する方法を変更する  
    現在は以下の3種類  
    * tf-idf（デフォルト）  
    * BM25  
    * 頻出度  
  ### * 実行（ズームのみ/再計算）
    上記の条件を適用する．  
    ズームのみの場合は，クラスタリング結果はそのままに適用する．  
    再計算の場合は，条件をもとに対象ツイートを選びなおし，クラスタリングを再度行う．  
  ### * クリア
    上記の条件を初期状態に戻す．  
  ### * tweetを見る
    実際のツイートを表示する．  
    各話題（色）ごとのツイートをタブでまとめて縦一列に表示する．  
    表示順は以下の3種類から選択する．  
    * 投稿時間順（デフォルト）
    * いいね順
    * 画像数順
    
## 2. trendHistory.py
    Twitterのトレンドのキーワードやクエリ，出現時間を取得し，CSV形式で保存する．  
    保存場所のパスは"../data/trend_list.csv"  
    実行すると，15分おきに日本のトレンドを取得できる．  
    取得してから7日以上経過したトレンドは自動で削除される．  
    日本以外のトレンドを取得する場合は，以下の行の（）内を変更する．  
    51行目trends = api.trends_place(23424856)[0]["trends"]  
  
## 3. tweetTest.py
    TwitterAPIを使用するときの初期設定を行う．  
    Twitterに登録した以下の値を入力する  
    CONSUMER_KEY="カスタマーキー"  
    CONSUMER_SECRET="カスタマーキーシークレット"  
    ACCESS_TOKEN="アクセストークン"  
    ACCESS_SECRET="アクセストークンシークレット"  

## 4. tweetToCSV.py
    trendHistry.pyで保存したCSVをもとに，ツイートを取得する．  
    32~34行目のname,query,timeに直接値を入れることで，通常のキーワード検索も可能．  
    保存場所のパスは"../data/（トレンド名:変数nameに相当）.csv"  
    画像は"../data/（トレンド名:変数nameに相当)/"に保存される．  
    画像を含めて数GB程度になるので容量に注意．  
  
## 5. wordDetection.py
    retweetClustering_GUI_img_html.pyで凡例抽出手法のBM25の実装のために必要．  
    以下のGitHubで公開されているプログラムをそのまま利用している．  
    "https://github.com/arosh/BM25Transformer/blob/master/bm25.py"  
  
  
