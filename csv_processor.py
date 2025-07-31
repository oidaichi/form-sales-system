import pandas as pd
import re
import hashlib
from urllib.parse import urlparse
import logging

# ロガー設定
# Flaskアプリケーションなど、呼び出し元で設定されたロガーを使用することを想定
logger = logging.getLogger(__name__)

# 期待されるCSVの列名リスト。この順番で処理されます。
EXPECTED_COLUMNS = [
    'company', 'url', 'contact_url', 'industry_class', 'postal_code',
    'address', 'phone', 'fax', 'business_tags', 'list_tags'
]


def read_and_prepare_csv(filepath):
    """
    CSVファイルを読み込み、ヘッダーを処理し、列数を調整する。

    Args:
        filepath (str): CSVファイルのパス。

    Returns:
        pandas.DataFrame or None: 処理済みのデータフレーム。エラーの場合はNone。
        str: 処理結果のメッセージ。
    """
    # 日本語環境でよく使われる文字コードを順番に試す
    encodings_to_try = ['utf-8-sig', 'utf-8', 'shift_jis', 'cp932', 'euc-jp']
    df = None
    used_encoding = None

    for encoding in encodings_to_try:
        try:
            # pandasでCSVを読み込む。ヘッダーは一旦なしとして読み込む。
            df = pd.read_csv(filepath, encoding=encoding, header=None, engine='python')
            used_encoding = encoding
            logger.info(f"CSVファイルの読み込みに成功しました。 (文字コード: {used_encoding})")
            break  # 成功したらループを抜ける
        except Exception as e:
            logger.debug(f"文字コード'{encoding}'での読み込みに失敗: {e}")
            continue

    if df is None:
        error_message = "ファイルの読み込みに失敗しました。サポートされている文字コード（UTF-8, Shift_JISなど）か確認してください。"
        logger.error(error_message)
        return None, error_message

    # 1行目がヘッダーに見えるか判定（'company'や'url'などの単語が含まれるか）
    try:
        if df.empty:
            return None, "CSVファイルが空です。"
        first_row_values = [str(val).lower() for val in df.iloc[0].values]
        if 'company' in first_row_values or 'url' in first_row_values:
            logger.info("1行目をヘッダーとして認識し、スキップします。")
            df = df.iloc[1:].reset_index(drop=True)
    except IndexError:
        return None, "CSVファイルが空か、ヘッダーのみのようです。"

    # 列数をチェックし、期待される列数（10列）に合わせる
    num_actual_cols = df.shape[1]
    num_expected_cols = len(EXPECTED_COLUMNS)

    if num_actual_cols < num_expected_cols:
        error_message = f"列数が不足しています。期待される列数は{num_expected_cols}ですが、ファイルには{num_actual_cols}列しかありません。"
        logger.error(error_message)
        return None, error_message
    
    if num_actual_cols > num_expected_cols:
        logger.warning(f"ファイルの列数が{num_actual_cols}列と多いため、最初の{num_expected_cols}列のみを使用します。")
        df = df.iloc[:, :num_expected_cols]

    # データフレームに列名を設定
    df.columns = EXPECTED_COLUMNS
    return df, "CSVファイルの読み込みと準備が完了しました。"


def clean_dataframe(df):
    """
    データフレームの値をきれいに整形（クレンジング）する。
    全てのカラムに適用し、欠損値の補正、空白・不正文字の除去を行う。

    Args:
        df (pandas.DataFrame): 入力データフレーム。

    Returns:
        pandas.DataFrame: クレンジング済みのデータフレーム。
    """
    logger.info("データのクレンジングを開始します。")
    
    # 全てのカラムを文字列型に変換し、前後の空白を削除
    # pd.NA, None, numpy.nan などもここで文字列 'nan', 'None' に変換される
    df = df.astype(str).apply(lambda x: x.str.strip())

    # 'nan', 'None', 'NA', 'N/A' といった文字列形式の欠損値を空文字列に置換
    # regex=False でリテラルマッチング
    df = df.replace(['nan', 'None', 'NA', 'N/A'], '', regex=False)

    # タブ、改行コード、全角スペースなどの不正文字を除去
    # 全角スペースは \u3000
    for col in df.columns:
        df[col] = df[col].apply(lambda x: re.sub(r'[\t\n\r\u3000]', '', x))
        # URL形式の補正: 不正なURLは空文字列に変換
    def _normalize_url(url_str):
        if not url_str:
            return ''
        try:
            parsed = urlparse(url_str)
            # スキームがない場合は 'http://' を追加して再パースを試みる
            if not parsed.scheme:
                parsed = urlparse('http://' + url_str)
            # 有効なスキームとネットロケーションがあるか確認
            if parsed.scheme in ['http', 'https'] and parsed.netloc:
                return parsed.geturl()
            else:
                return '' # 不正な形式は空文字列に
        except Exception:
            return '' # パースエラーも空文字列に

    if 'url' in df.columns:
        df['url'] = df['url'].apply(_normalize_url)
    if 'contact_url' in df.columns:
        df['contact_url'] = df['contact_url'].apply(_normalize_url)

    logger.info("データのクレンジングが完了しました。")
    return df


def validate_dataframe(df):
    """
    データフレームの内容が正しいか検証する。

    Args:
        df (pandas.DataFrame): 入力データフレーム。

    Returns:
        bool: 検証が成功したかどうか。
        str: 検証結果のメッセージ。
    """
    logger.info("データの検証を開始します。")
    # URLの形式をチェックする内部関数
    def _is_valid_url(url):
        if not url:
            return True  # 空欄は許容
        try:
            result = urlparse(url)
            # http/httpsで始まり、ドメイン名があるか
            return all([result.scheme in ['http', 'https'], result.netloc])
        except ValueError:
            return False

    # 必須項目（会社名とURL）が空でないかチェック
    if df['company'].eq('').any() or df['url'].eq('').any():
        error_message = "必須項目である「company」または「url」が空の行があります。"
        logger.error(error_message)
        return False, error_message

    # URLと連絡先URLの形式をチェック
    if not df['url'].apply(_is_valid_url).all():
        error_message = "「url」列に不正な形式のURLが含まれています。"
        logger.error(error_message)
        return False, error_message
    if not df['contact_url'].apply(_is_valid_url).all():
        error_message = "「contact_url」列に不正な形式のURLが含まれています。"
        logger.error(error_message)
        return False, error_message
    
    logger.info("データの検証が完了しました。")
    return True, "データの検証に成功しました。"


def remove_duplicate_rows(df):
    """
    重複している行を削除する。

    Args:
        df (pandas.DataFrame): 入力データフレーム。

    Returns:
        pandas.DataFrame: 重複削除後のデータフレーム。
    """
    initial_rows = len(df)
    # 「company」と「url」の組み合わせで重複を判定
    df = df.drop_duplicates(subset=['company', 'url'], keep='first')
    duplicates_removed = initial_rows - len(df)
    if duplicates_removed > 0:
        logger.info(f"{duplicates_removed}件の重複行を削除しました。")
    return df


def process_csv_file(filepath):
    """
    CSV処理のメイン関数。各ステップを順番に実行する。

    Args:
        filepath (str): CSVファイルのパス。

    Returns:
        pandas.DataFrame or None: 最終的に処理されたデータフレーム。エラーの場合はNone。
        str: 処理結果のメッセージ。
    """
    logger.info(f"CSVファイルの処理を開始します: {filepath}")

    # Step 1: ファイルを読み込み、列を準備する
    df, message = read_and_prepare_csv(filepath)
    if df is None:
        return None, message

    # Step 2: データをクレンジングする
    df = clean_dataframe(df)

    # Step 3: データを検証する
    is_valid, message = validate_dataframe(df)
    if not is_valid:
        return None, message

    # Step 4: 重複行を削除する
    df = remove_duplicate_rows(df)

    success_message = "CSVファイルの処理が正常に完了しました。"
    logger.info(success_message)
    return df, success_message