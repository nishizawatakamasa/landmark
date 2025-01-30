# landmark

## 概要 
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
### テンプレ1
```py
from landmark import Landmark

with Landmark() as lm:
    @lm.crawl
    def proc_foo():
        pass

    @lm.crawl_and_return_hrefs
    def bar():
        return [lm.attr('href', e) for e in lm.ss(r'')]
        
    @lm.crawl
    def scrp_baz():
        for e in lm.ss(r''):
            lm.save_row('../foo/bar', {
                'URL': lm.driver.current_url,
                '列名': lm.attr('textContent', lm.s_re(r'', r'', e)),
            })

    scrp_baz(bar(['']))
```

### テンプレ2
```py
from landmark import Landmark
from landmark.extra import extra as ex

c = ex.Counter()

with Landmark() as lm:
    @lm.crawl
    def proc_foo():
        pass

    @lm.crawl_and_return_hrefs
    def bar():
        return [lm.attr('href', e) for e in lm.ss(r'')]
        
    @lm.crawl
    def scrp_baz():
        for e in lm.ss(r''):
            c.count_up_num()
            lm.save_row('../foo/bar', {
                'No.': c.num,
                'URL': lm.driver.current_url,
                '列名': lm.attr('textContent', lm.s_re(r'', r'', e)),
            })
            ex.save_img(f'../foo/{c.num}_img_name.png', lm.s(r'', e))
            ex.save_screenshot(f'../foo/{c.num}_ss_name.png', lm.s(r'', e))
    
    c.init_num()
    scrp_baz(bar(['']))
```

### 使用例1
```py
from landmark import Landmark

with Landmark() as lm:   
    @lm.crawl_and_return_hrefs
    def prefectures():
        return [lm.attr('href', e) for e in lm.ss(r'li.item > ul > li > a')]
        
    @lm.crawl_and_return_hrefs
    def each_classroom():
        return [lm.attr('href', e) for e in lm.ss(r'.school-area h4 a')]

    @lm.crawl
    def scrp_classroom_info():
        lm.save_row('./classroom_info', {
            'URL': lm.driver.current_url,
            '教室名': lm.attr('textContent', lm.s(r'h1 .text01')),
            '住所': lm.attr('textContent', lm.s(r'.item .mapText')),
            '電話番号': lm.attr('textContent', lm.s(r'.item .phoneNumber')),
        })
    
    scrp_classroom_info(each_classroom(prefectures(['https://www.foobarbaz1.jp'])))
```

### 使用例2
```py
import time

from landmark import Landmark

with Landmark() as lm:
    @lm.crawl_and_return_hrefs
    def prefectures():
        return [lm.attr('href', e) for e in lm.ss(r'.region-item .pref-item a')]
        
    @lm.crawl_and_return_hrefs
    def each_office():
        lm.click(lm.s(r'#menu-btn'))
        time.sleep(2)
        return [lm.attr('href', e) for e in lm.ss(r'.container .detail-btn')]
        
    @lm.crawl
    def scrp_office_info():
        items_elem = lm.s(r'.foo .item-list') or lm.s(r'.bar.baz .items')
        lm.save_row('./scraped/office_info', {
            'URL': lm.driver.current_url,
            '支店名': lm.attr('textContent', lm.s(r'li:nth-last-of-type(1)', items_elem)),
            '住所': lm.attr('textContent', lm.next_sib(lm.s_re(r':is(h3.box, .inner dt)', r'住所'))),
        })

    scrp_office_info(each_office(prefectures(['https://www.foobarbaz2.com'])))
```
