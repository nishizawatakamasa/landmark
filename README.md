# landmark

## 概要
landmarkは、Seleniumを簡単に使うためのPythonモジュールです。  
ブラウザの自動操作、スクレイピング、データの保存などを簡単に行えます。

## インストール方法
landmarkと、landmarkの実行に必要な全てのPythonライブラリは、以下のコマンドでインストールできます。  
`pip install git+https://github.com/nishizawatakamasa/landmark`

## 必要な環境
landmarkの実行には、以下の環境が必要です。
* Python3.8以上
* ライブラリ
    * pandas(バージョン2.2.3以上)
    * selenium(バージョン4.27.1以上)
    * tqdm(バージョン4.67.1以上)
    * pyarrow(バージョン16.1.0以上)

## 実装例
```py
from selenium import webdriver as wd
from landmark import Landmark

options = wd.ChromeOptions()
options.add_argument('--incognito') # シークレットモード
# options.add_argument('--headless=new') # ヘッドレスモード
options.add_argument('--start-maximized') # ウィンドウ最大化
options.add_experimental_option('prefs', {'profile.managed_default_content_settings.images': 2}) # 画像読み込み無効
# options.add_argument(r'--user-data-dir=C:\Users\xxxx\AppData\Local\Google\Chrome\User Data') # 使用するユーザープロファイルの保存先パス
# options.add_argument('--profile-directory=Profile xx') # 使用するユーザープロファイルのディレクトリ名

with wd.Chrome(options=options) as driver:   
    lm = Landmark(driver)
    
    @lm.crawl
    def prefectures():
        return [lm.attr('href', elem) for elem in lm.ss('li.item > ul > li > a')]
        
    @lm.crawl
    def each_classroom():
        return [lm.attr('href', elem) for elem in lm.ss('.school-area h4 a')]
    
    @lm.crawl
    def scrape_classroom_info():
        lm.save_row('./classroom_info', {
            'URL': driver.current_url,
            '教室名': lm.attr('textContent', lm.s('h1 .text01')),
            '住所': lm.attr('innerText', lm.s('.item .mapText')),
            '電話番号': lm.attr('textContent', lm.s('.item .phoneNumber')),
            'HP': lm.attr('href', lm.s(r'a', lm.next_sib(lm.s_re(th, r'ホームページ')))),
        })
    
    scrape_classroom_info(each_classroom(prefectures(['https://www.foobarbaz1.jp'])))
```

## 基本的な使い方
### Landmarkクラス
landmarkモジュールは、Landmarkクラス1つによって構成されています。  
Landmarkクラスは、WebDriverのインスタンスを受け取ってSeleniumの処理をラップします。
```py
lm = Landmark(driver)
```

### Landmarkクラスのメソッド
Landmarkクラスは、以下のインスタンスメソッド19個によって構成されています。

#### 1. ss
セレクタで複数のWeb要素をリストで取得。存在しない場合は空のリスト。  
第二引数にWeb要素を渡すと、そのDOMサブセットからの取得となる。
```py
elems = lm.ss('li.item > ul > li > a')
```
#### 2. s
セレクタでWeb要素を取得。存在しない場合はNone。  
第二引数にWeb要素を渡すと、そのDOMサブセットからの取得となる。
```py
elem = lm.s('h1 .text01')
```
#### 3. re_filter
Web要素のリストを、指定した正規表現がtextContent属性値にマッチするかでフィルターにかける。  
マッチ判定は、textContent属性値をNFKC正規化して行われる。
```py
elems = lm.re_filter(r'住\s*所', elems)
```
#### 4. ss_re
セレクタと正規表現で複数のWeb要素をリストで取得。存在しない場合は空のリスト。  
正規表現によるWeb要素のフィルタリングにはre_filterが使われる。  
第三引数にWeb要素を渡すと、そのDOMサブセットからの取得となる。
```py
elems = lm.ss_re('li.item > ul > li > a', r'店\s*舗')
```
#### 5. s_re
セレクタと正規表現でWeb要素を取得。存在しない場合はNone。  
正規表現によるWeb要素のフィルタリングにはre_filterが使われる。  
第三引数にWeb要素を渡すと、そのDOMサブセットからの取得となる。
```py
elem = lm.s_re('table tbody tr th', r'住\s*所')
```
#### 6. attr
Web要素から任意の属性値を取得。
```py
text = lm.attr('textContent', elem)
```
#### 7. parent
渡されたWeb要素の親要素を取得。
```py
parent_elem = lm.parent(elem)
```
#### 8. prev_sib
渡されたWeb要素の兄要素を取得。
```py
prev_elem = lm.prev_sib(elem)
```
#### 9. next_sib
渡されたWeb要素の弟要素を取得。
```py
next_elem = lm.next_sib(elem)
```
#### 10. landmark
Web要素に任意のクラスを追加して目印にする。
```py
lm.landmark(elems, 'landmark-001')
```
#### 11. go_to
指定したURLに遷移する。
```py
lm.go_to('https://foobarbaz1.com')
```
#### 12. click
指定したWeb要素のclickイベントを発生させる。  
クリック時に新しいタブが開かれた場合は、そのタブに遷移(tab_switch=Falseで無効化)。
```py
lm.click(elem)
```
#### 13. switch_to
指定したiframe要素内に制御を移す。
```py
lm.switch_to(iframe_elem)
```
#### 14. scroll_to_view
指定したWeb要素をスクロールして表示する。
```py
lm.scroll_to_view(elem)
```
#### 15. next_hrefs1
ページのnextボタンのWeb要素を特定し、そのhref属性値に遷移しながら(by_click=Trueならばクリックしながら)取得していく。  
戻り値は、取得した全href属性値のリスト。  
第一引数にはnextボタンのWeb要素を取得して返す関数を指定する。
```py
hrefs = lm.next_hrefs1(func)
```
#### 16. next_hrefs2
ページのprevボタンとnextボタンのWeb要素を特定し、nextのhref属性値に遷移しながら(by_click=Trueならばクリックしながら)取得していく。  
戻り値は、取得した全href属性値のリスト。  
第一引数にはprevボタンとnextボタンのWeb要素を取得してリストで返す関数を指定する。
```py
hrefs = lm.next_hrefs2(func)
```
#### 17. save_row
パス指定したテーブルデータ(無い場合は作成される)に行を追加し、parquetファイルとして保存(拡張子の記述は不要)。
```py
lm.save_row('./scrape/foo', {
    '列名1': text01,
    '列名2': text02,
    '列名3': text03,
})
```
#### 18. use_tqdm
urlリストの各ページに対して処理を行っていく関数の進捗状況を表示する。
```py
for page_url in lm.use_tqdm(page_urls, func):
    lm.go_to(page_url)
    func()
```
#### 19. crawl
デコレータ。  
付与された関数は、URL文字列のリストを引数として受け取るようになる。  
URLリストを渡すと、そのURLに順番にアクセスしていき、各ページに対して関数の処理を実行するようになる。  
関数の処理がURL文字列のリストを返す場合、それら全てを結合したリストが最終的な戻り値となる。
```py
@lm.crawl
def foo():
    # 略
```
