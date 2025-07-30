import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

class FormDetector:
    def __init__(self, html_content, base_url):
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.base_url = base_url

    def detect_form_page(self):
        score = 0

        # Phase 1: URLパターン解析 (ここではbase_urlのみを考慮)
        url_keywords = [
            "contact", "inquiry", "form", "お問い合わせ", "問合せ", "consultation",
            "consult", "toiawase", "soudan", "apply", "request", "booking",
            "reservation", "estimate", "申込", "申し込み", "見積", "相談", "予約"
        ]
        for keyword in url_keywords:
            if keyword in self.base_url.lower():
                score += 2 # URLに含まれていたらスコア加算
                break

        # Phase 2: リンクテキスト解析
        link_keywords = [
            "お問い合わせ", "相談", "Contact Us", "Get in Touch",
            "お申し込み", "申込み", "ご相談", "問い合わせ", "コンタクト",
            "連絡", "フォーム", "見積", "資料請求", "無料相談", "ご予約", "予約",
            "contact", "inquiry", "form", "consultation", "apply",
            "register", "booking", "reservation", "estimate", "quote"
        ]
        for a_tag in self.soup.find_all('a'):
            link_text = a_tag.get_text(strip=True).lower()
            for keyword in link_keywords:
                if keyword in link_text:
                    score += 1 # リンクテキストに含まれていたらスコア加算
                    break

        # Phase 3: ページ内容解析
        # フォーム要素の存在確認
        if self.soup.find('form'):
            score += 3
        if self.soup.find_all(['input', 'textarea', 'select']):
            score += 2
        if self.soup.find_all(['input', 'button'], type='submit'):
            score += 2

        # HTMLコンテンツ内のキーワード密度分析 (簡易版)
        page_text = self.soup.get_text().lower()
        for keyword in url_keywords + link_keywords:
            if keyword in page_text:
                score += 0.5 # ページ内容に含まれていたらスコア加算

        # 閾値はREADME_システム概要.mdより7.0
        is_form_page = score >= 7.0
        return is_form_page, score

    def find_contact_links(self):
        contact_links = []
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
            link_text = a_tag.get_text(strip=True).lower()

            # URLパターンとリンクテキストの両方でチェック
            if any(keyword in href.lower() for keyword in link_keywords) or \
               any(keyword in link_text for keyword in link_keywords):
                full_url = urljoin(self.base_url, href)
                contact_links.append(full_url)
        return list(set(contact_links)) # 重複を排除
