import streamlit as st
import pandas as pd
import re
from datetime import datetime

# Streamlitのページ設定を最初に実行 (幅を広げる)
st.set_page_config(
    layout="wide",
    menu_items={
        'Get help': None,       # ヘルプを非表示
        'Report a bug': None,   # バグレポートを非表示
        'About': "Syslog Viewer developed with Streamlit.", # Aboutは残すかカスタマイズ
        # 'Deploy': None          # この行がエラーの原因なので削除します
    }
)

def parse_syslog_line(line):
    """
    Syslogの各行を解析し、辞書として返す関数。
    RFC 5424 に近い、詳細なタイムスタンプとANSIエスケープシーケンスに対応。
    """
    match = re.match(
        r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}[+\-]\d{2}:\d{2})\s+' # タイムスタンプ
        r'([\w\d\.-]+)\s+'                                             # ホスト名
        r'([\w\d\.]+)?(?:\[(\d+)\])?:\s+'                                # アプリ名[PID]:
        r'(.*)$',                                                      # 残りのメッセージ
        line
    )

    if match:
        timestamp_str, hostname, app_name_raw, pid, message_raw = match.groups()

        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except ValueError:
            timestamp = timestamp_str

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

# --- フィルタ管理用のヘルパー関数 ---
def add_filter():
    """新しい空のフィルタ条件を追加する"""
    st.session_state.filters.append({"keyword": "", "operator": "AND"})

def remove_filter(index):
    """指定されたインデックスのフィルタ条件を削除する"""
    if len(st.session_state.filters) > 1: # 最後の1つは残す
        st.session_state.filters.pop(index)
    else:
        # 最後のフィルタを削除しようとした場合は、キーワードをクリアするだけにする
        st.session_state.filters[0]["keyword"] = ""
        st.session_state.filters[0]["operator"] = "AND"

def update_filter_keyword(index):
    """フィルタキーワードが変更されたときにセッションステートを更新する"""
    st.session_state.filters[index]["keyword"] = st.session_state[f"filter_keyword_{index}"]

def update_filter_operator(index):
    """フィルタ演算子が変更されたときにセッションステートを更新する"""
    st.session_state.filters[index]["operator"] = st.session_state[f"filter_operator_{index}"]

def convert_wildcard_to_regex(pattern):
    """
    ユーザー入力のワイルドカード (*, ?) を正規表現に変換する
    他の正規表現の特殊文字はエスケープする
    """
    # 正規表現の特殊文字をエスケープする（ただし * と ? は除く）
    escaped_pattern = re.escape(pattern)
    
    # re.escape は * と ? もエスケープするので、その後で元に戻しつつ正規表現の .* と .? に変換
    escaped_pattern = escaped_pattern.replace(r'\*', '.*') # * を .* (0文字以上の任意の文字) に変換
    escaped_pattern = escaped_pattern.replace(r'\?', '.')  # ? を . (任意の1文字) に変換
    
    return escaped_pattern
# --- ヘルパー関数ここまで ---


def main():
    st.title("Syslog Filter")

    # ファイルロードとデータ解析をセッションステートで管理
    if 'df_original' not in st.session_state:
        st.session_state.df_original = None
        st.session_state.file_loaded_name = None

    # フィルタ条件のリストをセッションステートで管理
    if 'filters' not in st.session_state:
        st.session_state.filters = [{"keyword": "", "operator": "AND"}] # 初期状態で1つのフィルタを用意

    loaded_file = st.file_uploader("Syslog ファイルを選択してください", type=["log", "txt"])

    if loaded_file is not None and loaded_file.name != st.session_state.file_loaded_name:
        with st.spinner(f"ファイル '{loaded_file.name}' を読み込み中..."):
            stringio = loaded_file.getvalue().decode("utf-8")
            lines = stringio.splitlines()

            parsed_logs = []
            for line in lines:
                parsed = parse_syslog_line(line)
                if parsed:
                    parsed_logs.append(parsed)

            if parsed_logs:
                df = pd.DataFrame(parsed_logs)
                # タイムスタンプ列をdatetime型に変換
                if not isinstance(df["Timestamp"].iloc[0], datetime):
                    df["Timestamp"] = pd.to_datetime(df["Timestamp"])
                st.session_state.df_original = df
                st.session_state.file_loaded_name = loaded_file.name
                st.success(f"ファイル '{loaded_file.name}' を読み込みました。")
            else:
                st.warning("解析可能なSyslogエントリが見つかりませんでした。ファイル形式を確認してください。")
                st.session_state.df_original = None
                st.session_state.file_loaded_name = None
    elif loaded_file is None:
        # ファイルがクリアされた場合、セッションステートもクリア
        st.session_state.df_original = None
        st.session_state.file_loaded_name = None
        # フィルタも初期状態に戻す
        st.session_state.filters = [{"keyword": "", "operator": "AND"}]


    # データが読み込まれている場合のみ、フィルタリングと表示を行う
    if st.session_state.df_original is not None:
        df = st.session_state.df_original.copy() # オリジナルDataFrameのコピーを操作

        st.write(f"元のログの行数: {len(df)}行")

        # --- 動的な複数フィルタリング機能 ---
        st.subheader("ログフィルタリング")
        st.info("キーワードで **`*` は0文字以上の任意の文字、**`?` は任意の1文字**を表します。")


        # 検索対象カラムを選択（フィルタリングの高速化のため）
        search_cols = ['Hostname', 'AppName', 'Message']

        # フィルタ入力欄を動的に生成
        for i, filter_item in enumerate(st.session_state.filters):
            col_op, col_kw, col_btn = st.columns([1, 4, 1]) # 論理演算子、キーワード、削除ボタンのレイアウト

            with col_op:
                if i == 0:
                    st.write("") # 最初のフィルタには演算子を表示しない
                else:
                    st.selectbox(
                        "演算子",
                        ["AND", "OR"],
                        index=0 if filter_item["operator"] == "AND" else 1,
                        key=f"filter_operator_{i}",
                        label_visibility="collapsed", # ラベルを非表示にしてコンパクトに
                        on_change=update_filter_operator,
                        args=(i,)
                    )
            with col_kw:
                st.text_input(
                    "キーワード",
                    value=filter_item["keyword"],
                    key=f"filter_keyword_{i}",
                    label_visibility="collapsed", # ラベルを非表示にしてコンパクトに
                    on_change=update_filter_keyword,
                    args=(i,)
                )
            with col_btn:
                if len(st.session_state.filters) > 1: # フィルタが1つ以上ある場合のみ削除ボタンを表示
                    st.button("削除", key=f"remove_filter_{i}", on_click=remove_filter, args=(i,))
                else:
                    st.write("") # スペースを空ける

        st.button("フィルタ追加", on_click=add_filter)
        st.markdown("---") # 区切り線

        # フィルタリングロジック
        filtered_df = df
        active_filters = [f for f in st.session_state.filters if f["keyword"]] # キーワードが入力されているフィルタのみを対象

        if active_filters:
            # 検索対象カラムを結合して単一の文字列を作成 (一度だけ実行)
            combined_text_series = df[search_cols].fillna('').astype(str).agg(' '.join, axis=1)

            # 最初の条件で初期化
            # キーワードを正規表現に変換して検索
            first_keyword_regex = convert_wildcard_to_regex(active_filters[0]["keyword"])
            final_mask = combined_text_series.str.contains(first_keyword_regex, case=False, na=False, regex=True)

            # 2つ目以降の条件をAND/ORで結合
            for i in range(1, len(active_filters)):
                current_filter = active_filters[i]
                
                # キーワードを正規表現に変換して検索
                current_keyword_regex = convert_wildcard_to_regex(current_filter["keyword"])
                current_condition = combined_text_series.str.contains(current_keyword_regex, case=False, na=False, regex=True)
                
                current_operator = current_filter["operator"]

                if current_operator == "AND":
                    final_mask = final_mask & current_condition
                elif current_operator == "OR":
                    final_mask = final_mask | current_condition
            
            filtered_df = df[final_mask]

            st.write(f"フィルタリング後のログの行数: {len(filtered_df)}行")
        # --- 動的な複数フィルタリング機能ここまで ---

        # --- 表示行数の制限機能 ---
        # テーブルのデフォルト表示行数を2000に変更
        max_display_rows = st.slider("表示する最大行数", 100, 1000000, 2000)

        display_df = filtered_df
        if len(filtered_df) > max_display_rows:
            display_df = filtered_df.tail(max_display_rows) # 最新のN行を表示
            st.info(f"上位 {max_display_rows} 行のみ表示しています。")

        st.dataframe(display_df, use_container_width=True, height=1000)

        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="表示中のデータフレームをCSVでダウンロード",
            data=csv,
            file_name='filtered_syslog_data.csv',
            mime='text/csv',
        )
    else:
        st.info("Syslogファイルを選択してください。")

if __name__ == "__main__":
    main()