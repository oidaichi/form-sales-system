import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

class FormDetector:
    def __init__(self, html_content, base_url):
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.base_url = base_url

    def detect_form_page(self):
        """
        現在のページが問い合わせフォームページである可能性をスコアリングして判定する。
        """
        score = 0

        # フォーム要素の存在確認
        if self.soup.find('form'):
            score += 3
        if self.soup.find_all(['input', 'textarea', 'select']):
            score += 2
        if self.soup.find_all(['input', 'button'], type='submit'):
            score += 2

        # ページ内容内のキーワード分析
        page_text = self.soup.get_text().lower()
        keywords = [
            "お問い合わせ", "相談", "contact us", "get in touch",
            "お申し込み", "申込み", "ご相談", "問い合わせ", "コンタクト",
            "連絡", "フォーム", "見積", "資料請求", "無料相談", "ご予約", "予約",
            "contact", "inquiry", "form", "consultation", "apply",
            "register", "booking", "reservation", "estimate", "quote"
        ]
        for keyword in keywords:
            if keyword in page_text:
                score += 0.5

        # 閾値はREADME_システム概要.mdより7.0
        is_form_page = score >= 7.0
        return is_form_page, score

    def find_contact_links(self):
        """
        ページ内からお問い合わせページへのリンクを抽出し、スコアリングして返す。
        """
        potential_contact_links = {} # URLをキー、スコアを値とする辞書

        link_keywords = [
            "contact", "inquiry", "form", "お問い合わせ", "問合せ", "consultation",
            "consult", "toiawase", "soudan", "apply", "request", "booking",
            "reservation", "estimate", "申込", "申し込み", "見積", "相談", "予約",
            "Contact Us", "Get in Touch", "お申し込み", "申込み", "ご相談", "問い合わせ",
            "コンタクト", "連絡", "フォーム", "見積", "資料請求", "無料相談", "ご予約", "予約",
            "register", "booking", "reservation", "estimate", "quote"
        ]

        for a_tag in self.soup.find_all('a', href=True):
            href = a_tag['href']
            full_url = urljoin(self.base_url, href)

            # 無効なURLやファイルへのリンクはスキップ
            if not self._is_valid_http_url(full_url):
                continue
            
            link_score = 0
            link_text = a_tag.get_text(strip=True).lower()
            link_title = a_tag.get('title', '').lower()
            link_class = a_tag.get('class', [])
            link_id = a_tag.get('id', '').lower()

            # URL自体にキーワードが含まれるか
            for keyword in link_keywords:
                if keyword in full_url.lower():
                    link_score += 3
                    break # 複数ヒットしても1回だけ加算

            # リンクテキストにキーワードが含まれるか
            for keyword in link_keywords:
                if keyword in link_text:
                    link_score += 2
                    break

            # title属性にキーワードが含まれるか
            for keyword in link_keywords:
                if keyword in link_title:
                    link_score += 1
                    break
            
            # class属性やid属性にキーワードが含まれるか
            for cls in link_class:
                for keyword in link_keywords:
                    if keyword in cls.lower():
                        link_score += 1
                        break
            if any(keyword in link_id for keyword in link_keywords):
                link_score += 1

            # スコアが0より大きい場合のみ追加
            if link_score > 0:
                # 既に同じURLがある場合は、より高いスコアを保持
                if full_url not in potential_contact_links or link_score > potential_contact_links[full_url]:
                    potential_contact_links[full_url] = link_score
        
        # スコアの高い順にソートしてURLのリストを返す
        sorted_links = sorted(potential_contact_links.items(), key=lambda item: item[1], reverse=True)
        return [url for url, score in sorted_links]

    def _is_valid_http_url(self, url):
        """有効なHTTP/HTTPS URLであるかを確認するヘルパー関数"""
        try:
            parsed = urlparse(url)
            return all([parsed.scheme in ['http', 'https'], parsed.netloc]) and not re.search(r'\.(pdf|doc|docx|xls|xlsx|zip|rar|tar|gz|jpg|jpeg|png|gif|bmp|mp4|mp3)$', parsed.path.lower())
        except ValueError:
            return False