import functools
import re
import time
import unicodedata as ud
from collections.abc import Callable
from types import TracebackType
from typing import Self, Literal, Iterable

import pandas as pd
import tqdm
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import InvalidArgumentException, TimeoutException

class Landmark:
    '''ブラウザを自動操作するツール。

    Attributes:
        _driver:
            Chromeクラスのオブジェクト。プロパティとしてもアクセスする。
        _tables:
            辞書。キーはテーブルデータの保存名。値はスクレイピング結果の辞書を格納したリスト。
    '''
    def __init__(self, user_data_dir: str | None = None, profile_directory: str | None = None) -> None:
        '''初期化。

        Args:
            user_data_dir:
                使用するユーザープロファイルの保存先パス。
            profile_directory:
                使用するユーザープロファイルのディレクトリ名。
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
        self._driver: Chrome = Chrome(options=options)
        self._tables: dict[str, list[dict[str, str]]] = {}

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

    def attr(self, attr_name: Literal['textContent', 'innerText', 'href', 'src'] | str, elem: WebElement | None) -> str | None:
        '''Web要素から任意の属性値を取得。'''
        if elem:
            return attr.strip() if (attr := elem.get_attribute(attr_name)) else attr
        return None

    def parent(self, elem: WebElement | None) -> WebElement | None:
        '''渡されたWeb要素の親要素を取得。'''
        return self._driver.execute_script('return arguments[0].parentElement;', elem) if elem else None

    def prev_sib(self, elem: WebElement | None) -> WebElement | None:
        '''渡されたWeb要素の兄要素を取得。'''
        return self._driver.execute_script('return arguments[0].previousElementSibling;', elem) if elem else None

    def next_sib(self, elem: WebElement | None) -> WebElement | None:
        '''渡されたWeb要素の弟要素を取得。'''
        return self._driver.execute_script('return arguments[0].nextElementSibling;', elem) if elem else None

    def re_filter(self, pattern: str, elems: list[WebElement]) -> list[WebElement]:
        '''Web要素のtextContent属性値をNFKC正規化し、正規表現でフィルターにかける。'''
        return [elem for elem in elems if re.findall(pattern, ud.normalize('NFKC', self.attr('textContent', elem)))]

    def ss(self, selector: str, from_: Literal['driver'] | WebElement | None = 'driver') -> list[WebElement]:
        '''セレクタを使用し、DOM(全体かサブセット)からWeb要素をリストで取得。'''
        if from_ == 'driver':
            return self._driver.find_elements(By.CSS_SELECTOR, selector)
        return [] if from_ is None else from_.find_elements(By.CSS_SELECTOR, selector)

    def ss_re(self, selector: str, pattern: str, from_: Literal['driver'] | WebElement | None = 'driver') -> list[WebElement]:
        '''セレクタと正規表現を使用し、DOM(全体かサブセット)からWeb要素をリストで取得。'''
        return self.re_filter(pattern, self.ss(selector, from_))

    def s(self, selector: str, from_: Literal['driver'] | WebElement | None = 'driver') -> WebElement | None:
        '''セレクタを使用し、DOM(全体かサブセット)からWeb要素を取得。'''
        return elems[0] if (elems := self.ss(selector, from_)) else None

    def s_re(self, selector: str, pattern: str, from_: Literal['driver'] | WebElement | None = 'driver') -> WebElement | None:
        '''セレクタと正規表現を使用し、DOM(全体かサブセット)からWeb要素を取得。'''
        return elems[0] if (elems := self.ss_re(selector, pattern, from_)) else None

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

    def scroll_to_view(self, elem: WebElement | None) -> None:
        '''スクロールして、指定Web要素を表示する。'''
        if elem:
            self._driver.execute_script('arguments[0].scrollIntoView({behavior: "instant", block: "end", inline: "nearest"});', elem)
            time.sleep(1)

    def next_hrefs1(self, select_next_button: Callable[[], WebElement], by_click: bool = False) -> list[str]:
        '''nextボタン要素を特定し、そのhrefを開きながら(by_click=Trueならばクリックしながら)取得していく。'''
        hrefs = [self.driver.current_url]
        while True:
            next_ = select_next_button() if by_click else self.attr('href', select_next_button())
            if next_:
                self.click(next_) if by_click else self.go_to(next_)
                hrefs.append(self.driver.current_url)
            else:
                break
        return hrefs

    def next_hrefs2(self, select_prev_and_next_button: Callable[[], list[WebElement]], by_click: bool = False) -> list[str]:
        '''prev&nextボタン要素を特定し、nextのhrefを開きながら(by_click=Trueならばクリックしながら)取得していく。

        Note:
            *nextボタンの判別方法。\n
            1.最初はボタンが一つ。←それがnext。\n
            2.次からボタンが二つ。←二つ目がnext。\n
            3.最後にまたボタンが一つに。←それはprevだからnextは無し。
        '''
        hrefs = [self.driver.current_url]
        first_page = True
        while True:
            prev_and_next = select_prev_and_next_button() if by_click else [self.attr('href', elem) for elem in select_prev_and_next_button()]
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
            hrefs.append(self.driver.current_url)
        return hrefs

    def save_row(self, name_path: str, row: dict[str, str]) -> None:
        '''指定した名前のテーブルデータ(無い場合は作成される)に行を追加。行は列名と値が要素の辞書。テーブルデータはparquetファイルとして保存される。'''
        if name_path not in self._tables.keys():
            self._tables[name_path] = []
        self._tables[name_path].append(row)
        pd.DataFrame(self._tables[name_path]).to_parquet(f'{name_path}.parquet')

    def use_tqdm(self, items: Iterable, target_func: Callable) -> tqdm:
        '''繰り返し処理を行う関数の進捗状況を表示する。'''
        return tqdm.tqdm(items, desc=f'{target_func.__name__}', bar_format='{desc}  {percentage:3.0f}%  {elapsed}  {remaining}')

    def crawl(self, proc_page: Callable[[], list[str] | None]) -> Callable[[list[str]], list[str]]:
        '''page_urlsの各ページに対し、proc_pageが実行されるようになる。さらにproc_pageがhrefsを返す場合、それら全てを結合したリストを返すようになる。'''
        @functools.wraps(proc_page)
        def wrapper(page_urls: list[str]) -> list[str]:
            urls = []
            for page_url in self.use_tqdm(page_urls, proc_page):
                self.go_to(page_url)
                if type(hrefs := proc_page()) is list:
                    urls.extend(hrefs)
            return urls
        return wrapper
