# landmark

## 概要
Pythonのパッケージ。  
Seleniumのラッパー。  
少ないコードで色々できる。

## 機能
1. ブラウザの自動操作
1. クローリング
1. スクレイピング
1. スクレイピングしたデータの保存

## インストール方法
`pip install git+https://github.com/nishizawatakamasa/landmark`

## 使い方
### テンプレ
```py
from landmark import Landmark

with Landmark() as lm:
    @lm.crl
    def proc_foo():
        pass

    @lm.crl_h
    def bar():
        lm.save_hrefs(lm.hrefs(lm.ss(r'')))
        
    @lm.crl
    def scrp_baz():
        for e in lm.ss(r''):
            lm.count_up_num()
            lm.store_df_row({
                'No.': lm.num,
                '列名': lm.txt_c(lm.s_re(r'', r'', e)),
            })
            lm.store_img(f'../foo/{lm.num}_img_name.png', lm.s(r'', e))
            lm.store_screenshot(f'../foo/{lm.num}_ss_name.png', lm.s(r'', e))
    
    lm.init_num()
    lm.init_df_storage('../foo/bar.parquet')
    scrp_baz(bar(['']))
```

### 使用例1
```py
from landmark import Landmark

with Landmark() as lm:   
    @lm.crl_h
    def prefectures():
        lm.save_hrefs(lm.hrefs(lm.ss(r'li.item > ul > li > a')))
        
    @lm.crl_h
    def each_classroom():
        lm.save_hrefs(lm.hrefs(lm.ss(r'.school-area h4 a')))

    @lm.crl
    def scrp_classroom_info():
        lm.store_df_row({
            'URL': lm.driver.current_url,
            '教室名': lm.txt_c(lm.s(r'h1 .text01')),
            '住所': lm.txt_c(lm.s(r'.item .mapText')),
            '電話番号': lm.txt_c(lm.s(r'.item .phoneNumber')),
        })
    
    lm.init_df_storage('./classroom_info.parquet')
    scrp_classroom_info(each_classroom(prefectures(['https://www.foobarbaz1.jp'])))
```

### 使用例2
```py
import time

from landmark import Landmark

with Landmark() as lm:
    @lm.crl_h
    def prefectures():
        lm.save_hrefs(lm.hrefs(lm.ss(r'.region-item .pref-item a')))
        
    @lm.crl_h
    def each_office():
        lm.click(lm.s(r'#menu-btn'))
        time.sleep(2)
        lm.save_hrefs(lm.hrefs(lm.ss(r'.container .detail-btn')))
        
    @lm.crl
    def scrp_office_info():
        items_elem = lm.s(r'.foo .item-list') or lm.s(r'.bar.baz .items')
        lm.store_df_row({
            'URL': lm.driver.current_url,
            '支店名': lm.txt_c(lm.s(r'li:nth-last-of-type(1)', items_elem)),
            '住所': lm.txt_c(lm.next_sib(lm.s_re(r':is(h3.box, .inner dt)', r'住所'))),
        })

    lm.init_df_storage('./scraped/office_info.parquet')
    scrp_office_info(each_office(prefectures(['https://www.foobarbaz2.com'])))
```
