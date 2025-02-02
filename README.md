# landmark

## 概要 
Landmarkクラスは、WebDriverのインスタンスを受け取ってSeleniumの処理をラップします。

## 機能
1. ブラウザの自動操作
1. クローリング
1. スクレイピング
1. スクレイピングしたデータの保存

## インストール方法
`pip install git+https://github.com/nishizawatakamasa/landmark`

## 使い方

### 実装例
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
        return [lm.attr('href', e) for e in lm.ss('li.item > ul > li > a')]
        
    @lm.crawl
    def each_classroom():
        return [lm.attr('href', e) for e in lm.ss('.school-area h4 a')]
    
    @lm.crawl
    def scrape_classroom_info():
        lm.save_row('./classroom_info', {
            'URL': driver.current_url,
            '教室名': lm.attr('textContent', lm.s('h1 .text01')),
            '住所': lm.attr('textContent', lm.s('.item .mapText')),
            '電話番号': lm.attr('textContent', lm.s('.item .phoneNumber')),
        })
    
    scrape_classroom_info(each_classroom(prefectures(['https://www.foobarbaz1.jp'])))
```
