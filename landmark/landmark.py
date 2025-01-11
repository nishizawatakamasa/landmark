'''Chromeブラウザを自動操作するためのツール。

Template
--------
from landmark import Landmark

with Landmark() as lm:
    @lm.crl
    def proc_foo():
        pass

    @lm.crl_h
    def bar():
        lm.save_hrefs(lm.hrefs(lm.ss(r'')))
        
    @lm.crl
    def scrape_baz():
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
    scrape_baz(bar(['']))
'''
import functools
import re
import time
import tkinter as tk
import unicodedata as ud
from collections.abc import Callable, Generator
from tkinter import messagebox
from types import TracebackType
from typing import Final, NoReturn, Self, Literal, Iterable
from urllib.parse import urlencode

import pandas as pd
import requests
import tqdm
from requests.exceptions import InvalidSchema
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import InvalidArgumentException, TimeoutException

class Landmark:
    '''簡単にブラウザの自動操作ができる。
    
    Attributes:
        _driver:
            Chromeクラスのオブジェクト。プロパティとしてもアクセスする。
        _child_page_hrefs:
            子ページのhrefを格納してreturnするためのリスト。
        _count_up:
            1から順にカウントアップするジェネレータイテレータ。
        _df_path:
            parquetファイルとして保存するDataFrameのパス。
        _num:
            _count_upの値を格納し、スクレイピングの件数ごとに番号を振っていく。
        _value_dicts:
            スクレイピング結果の辞書を保存するリスト。
        _TQDM_BAR_FORMAT:
            tqdmの表示設定用。
    '''
    def __init__(self, user_data_dir: str | None = None, profile_directory: str | None = None, img_disp: bool = True) -> None:
        '''初期化メソッド。
        
        Args:
            user_data_dir:
                使用するユーザープロファイルの保存先パス。
            profile_directory:
                使用するユーザープロファイルのディレクトリ名。
            img_disp:
                ブラウザに画像を表示するかどうかをbool値で指定。
        Note:
            ※使用中のプロファイルはchrome://versionのプロフィールパス欄で確認できる。
            Chromeクラスをインスタンス化し、ウィンドウを起動。
        '''
        options: Options = Options()
        options.add_argument('--start-maximized')
        if user_data_dir:
            options.add_argument(fr'--user-data-dir={user_data_dir}')
        if profile_directory:
            options.add_argument(f'--profile-directory={profile_directory}')
        if not img_disp:
            options.add_experimental_option('prefs', {'profile.managed_default_content_settings.images': 2})
        self._driver: Chrome = Chrome(options=options)
        self._child_page_hrefs: list[str]
        self._count_up: Generator[int, None, NoReturn]
        self._df_path: str
        self._value_dicts: list[dict[str, str]]
        self._TQDM_BAR_FORMAT: Final[str] = '{desc}  {percentage:3.0f}%  {elapsed}  {remaining}'
        self._num: int
    
    def __enter__(self) -> Self:
        '''with文開始時にインスタンスを戻す（asエイリアスで受ける）。'''
        return self
    
    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None) -> None:
        '''with文終了時に、chrome driverのプロセスを完全終了。'''
        self._driver.quit()
    
    @property
    def driver(self):
        '''Chromeクラスのオブジェクト。'''
        return self._driver

    def extract(self, pattern: str, string: str) -> str | tuple[str]: 
        '''正規表現を使用し、文字列から部分文字列を一つだけ抽出。'''
        texts = re.findall(pattern, string)
        return texts[0] if texts else ''
    
    def _strip_and_normalize(self, text: str) -> str:
        '''テキストをstrip&NFKC正規化する。'''
        return ud.normalize('NFKC', text.strip())
    
    def attr_value(self, attr_name: str, elem: WebElement | None) -> str:
        '''Web要素から任意の属性値を取得。'''
        attr_value = elem.get_attribute(attr_name) if elem else ''
        return self._strip_and_normalize(attr_value) if attr_value else ''
    
    def txt_c(self, elem: WebElement | None) -> str:
        '''Web要素からtextContent属性値を取得。'''
        txt_c = elem.get_attribute('textContent') if elem else ''
        return self._strip_and_normalize(txt_c) if txt_c else ''
    
    def i_txt(self, elem: WebElement | None) -> str:
        '''Web要素からinnerText属性値を取得。'''
        i_txt = elem.get_attribute('innerText') if elem else ''
        return self._strip_and_normalize(i_txt) if i_txt else ''
    
    def href(self, elem: WebElement | None) -> str:
        '''Web要素からhref属性値を取得。'''
        href = elem.get_attribute('href') if elem else ''
        return href if href else ''
    
    def src(self, elem: WebElement | None) -> str:
        '''Web要素からsrc属性値を取得。'''
        src = elem.get_attribute('src') if elem else ''
        return src if src else ''
    
    def attr_values(self, attr_name: str, elems: list[WebElement]) -> list[str]:
        '''Web要素リストから任意の属性値リストを取得。'''
        return [self.attr_value(attr_name, elem) for elem in elems]
    
    def txt_cs(self, elems: list[WebElement]) -> list[str]:
        '''Web要素リストからtextContent属性値リストを取得。'''
        return [self.txt_c(elem) for elem in elems]
    
    def i_txts(self, elems: list[WebElement]) -> list[str]:
        '''Web要素リストからinnerText属性値リストを取得。'''
        return [self.i_txt(elem) for elem in elems]
    
    def hrefs(self, elems: list[WebElement]) -> list[str]:
        '''Web要素リストからhref属性値リストを取得。'''
        return [self.href(elem) for elem in elems]
    
    def srcs(self, elems: list[WebElement]) -> list[str]:
        '''Web要素リストからsrc属性値リストを取得。'''
        return [self.src(elem) for elem in elems]
    
    def parent(self, elem: WebElement | None) -> WebElement | None:
        '''渡されたWeb要素の親要素を取得。'''
        return self._driver.execute_script('return arguments[0].parentElement;', elem) if elem else None

    def prev_sib(self, elem: WebElement | None) -> WebElement | None:
        '''渡されたWeb要素の兄要素を取得。'''
        return self._driver.execute_script('return arguments[0].previousElementSibling;', elem) if elem else None

    def next_sib(self, elem: WebElement | None) -> WebElement | None:
        '''渡されたWeb要素の弟要素を取得。'''
        return self._driver.execute_script('return arguments[0].nextElementSibling;', elem) if elem else None

    def first(self, elems: list[WebElement]) -> WebElement | None:
        '''Web要素リストの中の、最初の一つを返す。'''
        return elems[0] if elems else None

    def re_filter(self, pattern: str, elems: list[WebElement]) -> list[WebElement]:
        '''Web要素を正規表現でフィルターにかける。'''
        return [elem for elem in elems if self.extract(pattern, self.txt_c(elem))]

    def ss(self, selector: str, from_: Literal['driver'] | WebElement | None = 'driver') -> list[WebElement]:
        '''セレクタを使用し、DOM(全体かサブセット)からWeb要素をリストで取得。'''
        if from_ == 'driver':
            return self._driver.find_elements(By.CSS_SELECTOR, selector)
        return [] if from_ is None else from_.find_elements(By.CSS_SELECTOR, selector)
    
    def ss_re(self, selector: str, pattern: str, from_: Literal['driver'] | WebElement | None = 'driver') -> list[WebElement]:
        '''ショートハンド。re_filter(ss())'''
        return self.re_filter(pattern, self.ss(selector, from_))

    def s(self, selector: str, from_: Literal['driver'] | WebElement | None = 'driver') -> WebElement | None:
        '''ショートハンド。first(ss())'''
        return self.first(self.ss(selector, from_))

    def s_re(self, selector: str, pattern: str, from_: Literal['driver'] | WebElement | None = 'driver') -> WebElement | None:
        '''ショートハンド。first(re_filter(ss()))'''
        return self.first(self.re_filter(pattern, self.ss(selector, from_)))
    
    def landmark(self, elems: list[WebElement], class_name: str) -> None:
        '''Web要素に任意のクラスを追加する。
        
        Note:
            このメソッドを利用することにより、Web要素のあらゆる取得条件をセレクタで表現できるようになる。
        '''
        for elem in elems:
            self._driver.execute_script(f'arguments[0].classList.add("{class_name}");', elem)
        
    def go_to(self, url: str) -> None:
        '''指定したURLに遷移。'''
        try:
            self._driver.get(url)
        except InvalidArgumentException as e:
            print(f'{type(e).__name__}: {e}')
        except TimeoutException as e:
            print(f'{type(e).__name__}: {e}')
        else:
            time.sleep(1)
    
    def create_sequential_urls(self, common_part_of_url_1: str, num_range: tuple[int], common_part_of_url_2: str = '') -> list[str]:
        '''連番URLを作成。
        
        Args:
            common_part_of_url_1:
                連番URLの共通部分(前半部分)。
            num_range:
                アンパックしてrangeの引数に渡し、連番を生成。
            common_part_of_url_2:
                連番URLの共通部分(後半部分、省略可)。
        '''
        return [common_part_of_url_1 + str(page_num) + common_part_of_url_2 for page_num in range(*num_range)]
    
    def create_google_search_url(self, search_words: list[str], english_search: bool = False, search_for_images: bool = False) -> str:
        '''指定した複数のワードでgoogle検索をした結果のURLを作成。
        
        Args:
            search_words:
                検索ワードのリスト。
            english_search:
                Trueで英語検索。
            search_for_images:
                Trueで画像検索。
        '''
        query_dict = {'q': ' '.join(search_words), 'udm': '1'}
        if english_search:
            query_dict['gl'] = 'us'
            query_dict['hl'] = 'en'
        if search_for_images:
            query_dict['udm'] = '2'
        query_string = urlencode(query_dict)
        return f'https://www.google.com/search?{query_string}'
    
    def create_google_map_search_url(self, search_words: list[str], english_search: bool = False) -> str:
        '''指定した複数のワードでgoogleマップ検索をした結果のURLを作成。
        
        Args:
            search_words:
                検索ワードのリスト。
            english_search:
                Trueで英語検索。
        '''
        query_dict = {'output': 'search', 'q': ' '.join(search_words)}
        if english_search:
            query_dict['gl'] = 'us'
            query_dict['hl'] = 'en'
        query_string = urlencode(query_dict)
        return f'https://maps.google.com/maps?{query_string}'

    def click(self, elem: WebElement, tab_switch: bool = True) -> None:
        '''指定したWeb要素をクリック(JavaScriptを使用し、要素のclickイベントを発生させる)。
        
        Note:
            クリック時に新しいタブが開かれた場合は、そのタブに遷移(tab_switch=Falseで無効化)。
        '''
        if elem:
            self._driver.execute_script('arguments[0].click();', elem)
            time.sleep(1)
            if tab_switch and len(self._driver.window_handles) == 2:
                self._driver.close()
                self._driver.switch_to.window(self._driver.window_handles[-1])
    
    def pause_proc(self, message: str) -> None:
        '''処理を一時停止(ダイアログを表示)。'''
        root = tk.Tk()
        root.attributes('-topmost', True)
        root.withdraw()
        messagebox.showinfo(message=message)
        root.destroy()
    
    def save_href(self, href: str) -> None:
        '''子ページのhrefを格納。crl_hと使用。'''
        self._child_page_hrefs.append(href)

    def save_hrefs(self, hrefs: list[str]) -> None:
        '''子ページのhrefリストを格納（結合）。crl_hと使用。'''
        self._child_page_hrefs.extend(hrefs)
    
    def save_next_hrefs1(self, select_next_button: Callable[[], WebElement], by_click: bool = False) -> None:
        '''子ページのhrefを取得して格納。crl_hと使用。
        
        Note:
            nextボタンをセレクタ(&パターン)で特定し、そのhrefを開いて(by_click=Trueならばクリックして)取得していく。\n
        '''
        self.save_href(self.driver.current_url)
        while True:
            next_ = select_next_button() if by_click else self.href(select_next_button())
            if next_:
                self.click(next_) if by_click else self.go_to(next_)
                self.save_href(self.driver.current_url)
            else:
                break

    def save_next_hrefs2(self, select_prev_and_next_button: Callable[[], list[WebElement]], by_click: bool = False) -> None:
        '''子ページのhrefを取得して格納。crl_hと使用。
        
        Note:
            prev&nextボタンをセレクタ(&パターン)で特定し、nextのhrefを開いて(by_click=Trueならばクリックして)取得していく。\n
            *nextボタンの判別方法。\n
            1.最初はボタンが一つ。←それがnext。\n
            2.次からボタンが二つ。←二つ目がnext。\n
            3.最後にまたボタンが一つに。←それはprevだからnextは無し。
        '''
        self.save_href(self.driver.current_url)
        first_page = True
        while True:
            prev_and_next = select_prev_and_next_button() if by_click else [self.href(elem) for elem in select_prev_and_next_button()]
            match len(prev_and_next):
                case 0:
                    break
                case 1:
                    if first_page:
                        next_ = prev_and_next[0]
                        first_page = False
                    else:
                        break
                case 2:
                    next_ = prev_and_next[1]
            self.click(next_) if by_click else self.go_to(next_)
            self.save_href(self.driver.current_url)
    
    def init_df_storage(self, df_path: str) -> None:
        '''DataFrameストレージの初期化。取得データから作成したDataFrameをparquetファイルとして保存したい場合に実行。'''
        self._value_dicts = []
        self._df_path = df_path

    def store_df_row(self, value_dict: dict[str, str]) -> None:
        '''_value_dictsに列名と値が要素のvalue_dictをappendし、DataFrameとして保存。crlと使用。'''
        self._value_dicts.append(value_dict)
        pd.DataFrame(self._value_dicts).to_parquet(self._df_path)
        
    def use_tqdm(self, items: Iterable, target_func: Callable) -> tqdm:
        '''繰り返し処理を行う関数の進捗状況を表示する。'''
        return tqdm.tqdm(items, desc=f'{target_func.__name__}', bar_format=self._TQDM_BAR_FORMAT)
    
    def crl(self, proc_page: Callable[[], None]) -> Callable[[list[str]], None]:
        '''渡されたpage_urlsの各ページに対し、proc_pageが実行されるようになる。'''
        @functools.wraps(proc_page)
        def wrapper(page_urls: list[str]) -> None:
            for page_url in self.use_tqdm(page_urls, proc_page):
                self.go_to(page_url)
                proc_page()
        return wrapper
    
    def crl_h(self, proc_page: Callable[[], None]) -> Callable[[list[str]], list[str]]:
        '''渡されたparent_page_urlsの各ページに対しproc_pageを実行し、取得した子ページのhrefをリストで返すようになる。'''
        @functools.wraps(proc_page)
        def wrapper(parent_page_urls: list[str]) -> list[str]:
            self._child_page_hrefs = []
            for parent_page_url in self.use_tqdm(parent_page_urls, proc_page):
                self.go_to(parent_page_url)
                proc_page()
            return self._child_page_hrefs
        return wrapper
    
    def store_img(self, img_path: str, img_elem: WebElement | None) -> None:
        '''渡されたimg要素から画像データを取得し、pngファイルとして保存。'''
        if img_elem:
            try:
                response = requests.get(img_elem.get_attribute('src'))
            except InvalidSchema as e:
                print(f'{type(e).__name__}: {e}')
            else:
                time.sleep(1)
                with open(img_path, 'wb') as f:
                    f.write(response.content)

    def store_screenshot(self, screenshot_path: str, target_elem: WebElement | None) -> None:
        '''渡されたWeb要素のスクリーンショットをpngファイルとして保存。'''
        if target_elem:
            self._driver.execute_script('arguments[0].scrollIntoView({behavior: "instant", block: "end", inline: "nearest"});', target_elem)
            time.sleep(3)
            target_elem.screenshot(screenshot_path)
            
    def _count_up_generator(self) -> Generator[int, None, NoReturn]:
        '''1から順にカウントアップするジェネレータ関数。'''
        count = 0
        while True:
            count += 1
            yield count
    
    def init_num(self) -> None:
        '''取得データ件数番号を初期化。'''
        self._count_up = self._count_up_generator()
        
    def count_up_num(self) -> None:
        '''取得データ件数番号を1からカウントアップ。'''
        self._num = next(self._count_up)
    
    @property
    def num(self):
        '''_count_upの値を格納し、スクレイピングの件数ごとに番号を振っていく。'''
        return self._num
    