# utils/log_parser_utils.py
import re
from datetime import datetime

# Syslogの正規表現パターン (既存コードと同一)
# NOTE: オリジナルのapp.pyの正規表現は少し異なっていたため、そちらに合わせます。
# アプリ名[PID]の部分がより柔軟になります。
SYSLOG_PATTERN = re.compile(
    r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}[+\-]\d{2}:\d{2})\s+' # Timestamp
    r'([\w\d\.-]+)\s+'                                                 # Hostname
    r'([\w\d\.]+)?(?:\[(\d+)\])?:\s+'                                  # AppName[PID]:
    r'(.*)$'                                                           # Message
)

def parse_syslog_line(log_line):
    """
    Syslogの1行をパースして辞書として返す。
    タイムスタンプはdatetimeオブジェクトに変換される。
    カラム名はオリジナルのapp.pyに合わせて大文字始まり。
    """
    match = SYSLOG_PATTERN.match(log_line)
    if match:
        timestamp_str, hostname, app_name_raw, pid, message_raw = match.groups()

        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except ValueError:
            timestamp = timestamp_str # パース失敗時は元の文字列を保持

        app_name = app_name_raw if app_name_raw else "Unknown"

        # メッセージからANSIエスケープシーケンスを除去
        cleaned_message = re.sub(r'\x1b\[[0-9;]*m', '', message_raw)

        return {
            "Timestamp": timestamp,
            "Hostname": hostname,
            "AppName": app_name,
            "PID": pid,
            "Message": cleaned_message
        }
    return None