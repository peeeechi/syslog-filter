# app_pages/existing_filter_page.py
import streamlit as st
import pandas as pd
import re
from datetime import datetime # datetimeオブジェクトを扱うため

# utilsからparse_syslog_lineをインポート
from utils.log_parser_utils import parse_syslog_line

# --- フィルタ管理用のヘルパー関数 (オリジナルのapp.pyからコピー) ---
def add_filter():
    """新しい空のフィルタ条件を追加する"""
    st.session_state.filters_keyword_page.append({"keyword": "", "operator": "AND"})

def remove_filter(index):
    """指定されたインデックスのフィルタ条件を削除する"""
    if len(st.session_state.filters_keyword_page) > 1: # 最後の1つは残す
        st.session_state.filters_keyword_page.pop(index)
    else:
        # 最後のフィルタを削除しようとした場合は、キーワードをクリアするだけにする
        st.session_state.filters_keyword_page[0]["keyword"] = ""
        st.session_state.filters_keyword_page[0]["operator"] = "AND"

def update_filter_keyword(index):
    """フィルタキーワードが変更されたときにセッションステートを更新する"""
    st.session_state.filters_keyword_page[index]["keyword"] = st.session_state[f"filter_keyword_{index}"]

def update_filter_operator(index):
    """フィルタ演算子が変更されたときにセッションステートを更新する"""
    st.session_state.filters_keyword_page[index]["operator"] = st.session_state[f"filter_operator_{index}"]

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


def run():
    st.title("Syslog Filter (キーワードフィルタリング)") # オリジナルと同じタイトル

    # ログデータの取得 (st.session_state.df を利用)
    # df_original は main_app.py の st.session_state.df に相当
    df_original = st.session_state.df if 'df' in st.session_state and st.session_state.df is not None else None

    # フィルタ条件のリストをセッションステートで管理 (キーをユニーク化)
    if 'filters_keyword_page' not in st.session_state:
        st.session_state.filters_keyword_page = [{"keyword": "", "operator": "AND"}] # 初期状態で1つのフィルタを用意

    # データが読み込まれている場合のみ、フィルタリングと表示を行う
    if df_original is not None:
        df = df_original.copy() # オリジナルDataFrameのコピーを操作

        st.write(f"元のログの行数: {len(df)}行")

        # --- 動的な複数フィルタリング機能 ---
        st.subheader("ログフィルタリング")
        st.info("キーワードで **`*` は0文字以上の任意の文字、**`?` は任意の1文字**を表します。")

        # 検索対象カラムを選択（オリジナルのapp.pyと同じ）
        search_cols = ['Hostname', 'AppName', 'Message']

        # フィルタ入力欄を動的に生成
        for i, filter_item in enumerate(st.session_state.filters_keyword_page):
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
                if len(st.session_state.filters_keyword_page) > 1: # フィルタが1つ以上ある場合のみ削除ボタンを表示
                    st.button("削除", key=f"remove_filter_{i}", on_click=remove_filter, args=(i,))
                else:
                    st.write("") # スペースを空ける

        st.button("フィルタ追加", on_click=add_filter, key="add_filter_button_keyword_page") # キーをユニーク化
        st.markdown("---") # 区切り線

        # フィルタリングロジック
        filtered_df = df
        active_filters = [f for f in st.session_state.filters_keyword_page if f["keyword"]] # キーワードが入力されているフィルタのみを対象

        if active_filters:
            # 検索対象カラムを結合して単一の文字列を作成 (一度だけ実行)
            # NOTE: オリジナルapp.pyのロジックを忠実に再現
            combined_text_series = df[search_cols].fillna('').astype(str).agg(' '.join, axis=1)

            # 最初の条件で初期化
            first_keyword_regex = convert_wildcard_to_regex(active_filters[0]["keyword"])
            final_mask = combined_text_series.str.contains(first_keyword_regex, case=False, na=False, regex=True)

            # 2つ目以降の条件をAND/ORで結合
            for i in range(1, len(active_filters)):
                current_filter = active_filters[i]
                
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

        # --- 表示行数の制限機能 (オリジナルと同じ) ---
        # テーブルのデフォルト表示行数を2000に変更
        max_display_rows = st.slider("表示する最大行数", 100, 1000000, 2000) # スライダーの範囲とデフォルト値もオリジナルに合わせる

        display_df = filtered_df
        if len(filtered_df) > max_display_rows:
            display_df = filtered_df.tail(max_display_rows) # 最新のN行を表示
            st.info(f"上位 {max_display_rows} 行のみ表示しています。") # オリジナルと同じメッセージ

        st.dataframe(display_df, use_container_width=True, height=1000) # use_container_widthとheightもオリジナルに合わせる

        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="表示中のデータフレームをCSVでダウンロード", # ラベルもオリジナルに合わせる
            data=csv,
            file_name='filtered_syslog_data.csv', # ファイル名もオリジナルに合わせる
            mime='text/csv',
            key="download_filtered_output_csv_keyword_page" # キーをユニーク化
        )
    else:
        st.warning("ログデータが読み込まれていません。「データ読み込み」ページでファイルをアップロードしてください。")