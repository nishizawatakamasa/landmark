'''Chromeブラウザを自動操作するためのツール。'''
import functools
import re
import time
import unicodedata as ud
from collections.abc import Callable
from types import TracebackType
from typing import Final, Self, Literal, Iterable

import pandas as pd
import tqdm
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
        _pq_path:
            (DataFrame経由で)保存するparquetファイルのパス。
        _value_dicts:
            スクレイピング結果の辞書を保存するリスト。
        _TQDM_BAR_FORMAT:
            tqdmの表示設定用。
    '''
    def __init__(self, user_data_dir: str | None = None, profile_directory: str | None = None, img_disp: bool = True) -> None:
        '''初期化。
        
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
        self._pq_path: str
        self._value_dicts: list[dict[str, str]]
        self._TQDM_BAR_FORMAT: Final[str] = '{desc}  {percentage:3.0f}%  {elapsed}  {remaining}'
    
    def __enter__(self) -> Self:
        '''with文開始時にインスタンスを戻す（asエイリアスで受ける）。'''
        return self
    
    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None) -> None:
        '''with文終了時に、chrome driverのプロセスを完全終了。'''
        self._driver.quit()
    
    @property
    def driver(self) -> Chrome:
        '''Chromeクラスのオブジェクト。'''
        return self._driver

    def extract(self, pattern: str, string: str) -> str | tuple[str]: 
        '''正規表現を使用し、文字列から部分文字列を一つだけ抽出。'''
        texts = re.findall(pattern, string)
        return texts[0] if texts else ''
    
    def attr_value(self, attr_name: str, elem: WebElement | None) -> str:
        '''Web要素から任意の属性値を取得。'''
        if elem:
            if attr_value := elem.get_attribute(attr_name):
                return attr_value.strip()
        return ''
    
    def txt_c(self, elem: WebElement | None) -> str:
        '''Web要素からtextContent属性値を取得。'''
        return self.attr_value('textContent', elem)
    
    def i_txt(self, elem: WebElement | None) -> str:
        '''Web要素からinnerText属性値を取得。'''
        return self.attr_value('innerText', elem)
    
    def href(self, elem: WebElement | None) -> str:
        '''Web要素からhref属性値を取得。'''
        return self.attr_value('href', elem)
    
    def src(self, elem: WebElement | None) -> str:
        '''Web要素からsrc属性値を取得。'''
        return self.attr_value('src', elem)
    
    def attr_values(self, attr_name: str, elems: list[WebElement]) -> list[str]:
        '''Web要素リストから任意の属性値リストを取得。'''
        return [self.attr_value(attr_name, elem) for elem in elems]
    
    def txt_cs(self, elems: list[WebElement]) -> list[str]:
        '''Web要素リストからtextContent属性値リストを取得。'''
        return self.attr_values('textContent', elems)
    
    def i_txts(self, elems: list[WebElement]) -> list[str]:
        '''Web要素リストからinnerText属性値リストを取得。'''
        return self.attr_values('innerText', elems)
    
    def hrefs(self, elems: list[WebElement]) -> list[str]:
        '''Web要素リストからhref属性値リストを取得。'''
        return self.attr_values('href', elems)
    
    def srcs(self, elems: list[WebElement]) -> list[str]:
        '''Web要素リストからsrc属性値リストを取得。'''
        return self.attr_values('src', elems)
    
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
        '''Web要素のtextContent属性値をNFKC正規化し、正規表現でフィルターにかける。'''
        return [elem for elem in elems if self.extract(pattern, ud.normalize('NFKC', self.txt_c(elem)))]

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
    
    def switch_to(self, iframe_elem: WebElement) -> None:
        '''指定したiframeの中に制御を移す。'''
        self.scroll_to_view(iframe_elem)
        if iframe_elem:
            self._driver.switch_to.frame(iframe_elem)
    
    def switch_to_parent(self) -> None:
        '''一つ上の親フレームに制御を移す。'''
        self._driver.switch_to.parent_frame()
        
    def switch_to_top(self) -> None:
        '''トップフレームに制御を移す。'''
        self._driver.switch_to.default_content()
    
    def scroll_to_view(self, elem: WebElement | None) -> None:
        '''スクロールして、指定Web要素を表示する。'''
        if elem:
            self._driver.execute_script('arguments[0].scrollIntoView({behavior: "instant", block: "end", inline: "nearest"});', elem)
            time.sleep(1)
            
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
            prev_and_next = select_prev_and_next_button() if by_click else self.hrefs(select_prev_and_next_button())
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
    
    def init_pq_storage(self, pq_path: str) -> None:
        '''Parquetストレージの初期化。取得データをparquetファイルとして保存したい場合に実行。'''
        self._value_dicts = []
        self._pq_path = pq_path

    def store_pq_row(self, value_dict: dict[str, str]) -> None:
        '''_value_dictsに列名と値が要素のvalue_dictをappendし、DataFrame経由でparquetファイルとして保存。crlと使用。'''
        self._value_dicts.append(value_dict)
        pd.DataFrame(self._value_dicts).to_parquet(self._pq_path)
        
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
    