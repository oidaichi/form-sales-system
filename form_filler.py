import re
import asyncio
import random
from datetime import datetime, timedelta

class FormFiller:
    def __init__(self, page, data):
        self.page = page # Playwright page object
        self.data = data

    async def fill_form(self):
        # 企業名フィールド検出
        await self._fill_field_by_patterns(
            self.data['company_data']['target_company'],
            name_patterns=['company', 'company_name', 'corporation'],
            id_patterns=['company', 'corp', 'organization'],
            placeholder_patterns=['会社名', '企業名', '法人名', 'Company Name'],
            label_patterns=['会社', '企業', '法人', '組織']
        )

        # 担当者名フィールド検出
        # 分割フィールド対応: sei(姓), mei(名), first_name, last_name
        # ここでは簡易的にsender_nameをそのまま入力
        await self._fill_field_by_patterns(
            self.data['company_data']['sender_name'],
            name_patterns=['name', 'your_name', 'contact_name', 'representative', 'sei', 'mei', 'first_name', 'last_name'],
            placeholder_patterns=['お名前', '氏名', '担当者名', '代表者名', 'Your Name'],
            label_patterns=['氏名', 'お名前', '担当者名']
        )
        # ふりがなフィールド
        await self._fill_field_by_patterns(
            self.data['company_data']['sender_furigana'],
            name_patterns=['furigana', 'kana', 'reading'],
            placeholder_patterns=['ふりがな', 'フリガナ', 'カナ'],
            label_patterns=['ふりがな', 'フリガナ']
        )

        # メールアドレスフィールド検出
        await self._fill_email_field(self.data['company_data']['sender_email'])

        # 電話番号フィールド検出
        await self._fill_field_by_patterns(
            self.data['company_data']['sender_phone'],
            name_patterns=['phone', 'tel', 'telephone', 'mobile'],
            placeholder_patterns=['電話番号', 'TEL', 'Phone Number'],
            label_patterns=['電話番号']
        )

        # 住所関連フィールド検出
        await self._fill_field_by_patterns(
            self.data['company_data']['sender_postal_code'],
            name_patterns=['zip', 'postal_code', 'postcode', '郵便番号'],
            placeholder_patterns=['郵便番号'],
            label_patterns=['郵便番号']
        )
        await self._fill_field_by_patterns(
            self.data['company_data']['sender_address'],
            name_patterns=['address', 'location', '住所'],
            placeholder_patterns=['住所'],
            label_patterns=['住所']
        )

        # メッセージフィールド検出
        await self._fill_message_field(self.data['message_data']['message'])

        # 選択フィールド検出 (問い合わせ種別など)
        await self._select_option_by_keywords(
            self.data['form_defaults']['inquiry_type'],
            name_patterns=['inquiry_type', 'consultation_type'],
            label_patterns=['問い合わせ種別', 'ご相談内容']
        )

        # プライバシーポリシー同意チェックボックス
        if self.data['form_defaults']['privacy_agreement']:
            await self._check_checkbox_by_keywords(
                ['privacy', '個人情報', '同意', '規約', 'プライバシーポリシー']
            )

        # ニュースレター購読チェックボックス
        if not self.data['form_defaults']['newsletter_subscription']:
            await self._uncheck_checkbox_by_keywords(
                ['newsletter', 'メルマガ', '購読']
            )

        # 日付フィールド (現在日時から7-9営業日後の平日を自動設定)
        await self._fill_date_field()

        # 時間フィールド (デフォルト13:00を設定)
        await self._fill_time_field("13:00")

    async def _fill_field_by_patterns(self, value, name_patterns=None, id_patterns=None, placeholder_patterns=None, label_patterns=None, input_type=None):
        if not value:
            return

        selectors = []
        if name_patterns:
            selectors.extend([f"[name*=\"{p}\"]" for p in name_patterns])
        if id_patterns:
            selectors.extend([f"#{p}" for p in id_patterns])
        if placeholder_patterns:
            selectors.extend([f"[placeholder*=\"{p}\"]" for p in placeholder_patterns])
        if label_patterns:
            selectors.extend([item for p in label_patterns for item in [f"label:has-text(\"{p}\") + input", f"label:has-text(\"{p}\") + textarea", f"label:has-text(\"{p}\") + select"]])

        if input_type:
            selectors = [f"input[type=\"{input_type}\"]" + s for s in selectors]

        for selector_list in selectors:
            if isinstance(selector_list, list):
                for selector in selector_list:
                    locator = self.page.locator(selector).first
                    if await locator.is_visible():
                        await self._type_human_like(locator, value)
                        return True
            else:
                locator = self.page.locator(selector_list).first
                if await locator.is_visible():
                    await self._type_human_like(locator, value)
                    return True
        return False

    async def _type_human_like(self, locator, text):
        await asyncio.sleep(random.uniform(0.1, 0.3)) # クリック前の待機
        await locator.click()
        await locator.press("Control+A") # 全選択
        await locator.press("Delete") # クリア
        for char in text:
            await locator.type(char, delay=random.uniform(50, 150)) # 1文字ずつランダム速度で入力
        await asyncio.sleep(random.uniform(0.3, 0.8)) # 操作間隔

    async def _fill_email_field(self, email):
        if not email:
            return
        # input type="email"を優先
        if await self._fill_field_by_patterns(email, input_type="email"):
            return
        await self._fill_field_by_patterns(
            email,
            name_patterns=['email', 'mail', 'e_mail', 'contact_email'],
            placeholder_patterns=['メールアドレス', 'Email'],
            label_patterns=['メールアドレス']
        )
        # 確認用フィールド
        await self._fill_field_by_patterns(
            email,
            name_patterns=['email_confirm', 'email2', 'confirm_email'],
            placeholder_patterns=['メールアドレス確認', 'Confirm Email'],
            label_patterns=['メールアドレス確認']
        )

    async def _fill_message_field(self, message):
        if not message:
            return
        # textarea要素を優先
        locator = self.page.locator("textarea").first
        if await locator.is_visible():
            await self._type_human_like(locator, message)
            return
        await self._fill_field_by_patterns(
            message,
            name_patterns=['message', 'content', 'inquiry', 'details', 'comment'],
            placeholder_patterns=['メッセージ', 'お問い合わせ内容', 'ご相談内容'],
            label_patterns=['お問い合わせ内容', 'メッセージ']
        )

    async def _select_option_by_keywords(self, value, name_patterns=None, label_patterns=None):
        if not value:
            return

        selectors = []
        if name_patterns:
            selectors.extend([f"select[name*=\"{p}\"]" for p in name_patterns])
            selectors.extend([f"input[type=\"radio\"][name*=\"{p}\"]" for p in name_patterns])

        if label_patterns:
            selectors.extend([item for p in label_patterns for item in [f"label:has-text(\"{p}\") + select", f"label:has-text(\"{p}\") + input[type=\"radio\"]"]])

        for selector_list in selectors:
            if isinstance(selector_list, list):
                for selector in selector_list:
                    locator = self.page.locator(selector).first
                    if await locator.is_visible():
                        if await locator.evaluate("el => el.tagName === 'SELECT'"):
                            await locator.select_option(value=value) # valueで選択
                        elif await locator.evaluate("el => el.type === 'radio'"):
                            # ラジオボタンの場合、valueまたはlabel textで選択
                            radio_locator = self.page.locator(f"{selector}[value=\"{value}\"]")
                            if not await radio_locator.is_visible():
                                radio_locator = self.page.locator(f"label:has-text(\"{value}\") > input[type=\"radio\"]")
                            if await radio_locator.is_visible():
                                await radio_locator.check()
                        await asyncio.sleep(random.uniform(0.3, 0.8))
                        return True
            else:
                locator = self.page.locator(selector_list).first
                if await locator.is_visible():
                    if await locator.evaluate("el => el.tagName === 'SELECT'"):
                        await locator.select_option(value=value)
                    elif await locator.evaluate("el => el.type === 'radio'"):
                        radio_locator = self.page.locator(f"{selector_list}[value=\"{value}\"]")
                        if not await radio_locator.is_visible():
                            radio_locator = self.page.locator(f"label:has-text(\"{value}\") > input[type=\"radio\"]")
                        if await radio_locator.is_visible():
                            await radio_locator.check()
                    await asyncio.sleep(random.uniform(0.3, 0.8))
                    return True
        return False

    async def _check_checkbox_by_keywords(self, keywords):
        for keyword in keywords:
            locator = self.page.locator(f"input[type=\"checkbox\"]:has-text(\"{keyword}\")").first
            if not await locator.is_visible():
                locator = self.page.locator(f"label:has-text(\"{keyword}\") > input[type=\"checkbox\"]").first
            if await locator.is_visible() and not await locator.is_checked():
                await locator.check()
                await asyncio.sleep(random.uniform(0.3, 0.8))
                return True
        return False

    async def _uncheck_checkbox_by_keywords(self, keywords):
        for keyword in keywords:
            locator = self.page.locator(f"input[type=\"checkbox\"]:has-text(\"{keyword}\")").first
            if not await locator.is_visible():
                locator = self.page.locator(f"label:has-text(\"{keyword}\") > input[type=\"checkbox\"]").first
            if await locator.is_visible() and await locator.is_checked():
                await locator.uncheck()
                await asyncio.sleep(random.uniform(0.3, 0.8))
                return True
        return False

    async def _fill_date_field(self):
        # 現在日時から7-9営業日後の平日を自動設定
        today = datetime.now()
        target_date = today
        days_added = 0
        while days_added < 9: # 最大9日後まで探す
            target_date += timedelta(days=1)
            if target_date.weekday() < 5: # 月曜(0)から金曜(4)まで
                days_added += 1
            if days_added >= 7: # 7営業日以上
                break

        date_str = target_date.strftime("%Y-%m-%d") # YYYY-MM-DD形式

        # input[type="date"]を優先
        if await self._fill_field_by_patterns(date_str, input_type="date"):
            return
        # その他の日付関連フィールド
        await self._fill_field_by_patterns(
            date_str,
            name_patterns=['date', 'reserve_date', 'appointment_date'],
            placeholder_patterns=['日付', 'YYYY-MM-DD'],
            label_patterns=['日付', '予約日']
        )

    async def _fill_time_field(self, time_str):
        # input[type="time"]を優先
        if await self._fill_field_by_patterns(time_str, input_type="time"):
            return
        # その他の時間関連フィールド
        await self._fill_field_by_patterns(
            time_str,
            name_patterns=['time', 'reserve_time', 'appointment_time'],
            placeholder_patterns=['時間', 'HH:MM'],
            label_patterns=['時間', '予約時間']
        )

    async def find_and_submit_form(self):
        submit_selectors = [
            "input[type=\"submit\"]",
            "button[type=\"submit\"]",
            "button:has-text(\"送信\")",
            "button:has-text(\"確認\")",
            "button:has-text(\"申し込み\")",
            "button:has-text(\"問い合わせ\")",
            "button:has-text(\"Submit\")",
            "button:has-text(\"Send\")",
            "button:has-text(\"確認画面\")",
            "button:has-text(\"確認画面へ\")",
            "button:has-text(\"確認する\")",
            "button:has-text(\"次へ\")",
            "button:has-text(\"Continue\")",
            "button:has-text(\"この内容で送信\")",
            "button:has-text(\"送信する\")",
            "button:has-text(\"Apply\")",
            "button:has-text(\"Register\")",
            "input[value=\"送信\"]",
            "input[value=\"確認\"]",
            "input[value=\"申込\"]",
            "input[value=\"Submit\"]",
            ".submit",
            ".send",
            ".apply",
            ".confirm"
        ]

        for selector in submit_selectors:
            locator = self.page.locator(selector).first
            if await locator.is_visible() and await locator.is_enabled():
                await asyncio.sleep(random.uniform(0.1, 0.3)) # クリック前の待機
                await locator.click()
                await asyncio.sleep(random.uniform(0.3, 0.8)) # 操作間隔
                return True
        return False
