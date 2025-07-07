# src/app_pages/existing_filter_page.py
import streamlit as st
import pandas as pd
import re
from datetime import datetime

# utilsからparse_syslog_lineをインポート
from src.utils.log_parser_utils import parse_syslog_line

# --- フィルタ管理用のヘルパー関数 (オリジナルのapp.pyからコピー) ---
def add_filter():
    st.session_state.filters_keyword_page.append({"keyword": "", "operator": "AND"})

def remove_filter(index):
    if len(st.session_state.filters_keyword_page) > 1:
        st.session_state.filters_keyword_page.pop(index)
    else:
        st.session_state.filters_keyword_page[0]["keyword"] = ""
        st.session_state.filters_keyword_page[0]["operator"] = "AND"

def update_filter_keyword(index):
    st.session_state.filters_keyword_page[index]["keyword"] = st.session_state[f"filter_keyword_{index}"]

def update_filter_operator(index):
    st.session_state.filters_keyword_page[index]["operator"] = st.session_state[f"filter_operator_{index}"]

def convert_wildcard_to_regex(pattern):
    escaped_pattern = re.escape(pattern)
    escaped_pattern = escaped_pattern.replace(r'\*', '.*')
    escaped_pattern = escaped_pattern.replace(r'\?', '.')
    return escaped_pattern
# --- ヘルパー関数ここまで ---

def run():
    st.title("Syslog Filter (キーワードフィルタリング)")

    df_source = st.session_state.df if 'df' in st.session_state and st.session_state.df is not None else pd.DataFrame()

    # --- 修正箇所: filters_keyword_page の初期化をここへ移動 ---
    if 'filters_keyword_page' not in st.session_state:
        st.session_state.filters_keyword_page = [{"keyword": "", "operator": "AND"}]
    # ----------------------------------------------------

    if not df_source.empty:
        st.write(f"元のログの行数: {len(df_source)}行")

        st.subheader("ログフィルタリング")
        st.info("キーワードで **`*` は0文字以上の任意の文字、**`?` は任意の1文字**を表します。")

        search_cols = ['Hostname', 'AppName', 'Message']

        for i, filter_item in enumerate(st.session_state.filters_keyword_page):
            col_op, col_kw, col_btn = st.columns([1, 4, 1])

            with col_op:
                if i == 0:
                    st.write("")
                else:
                    st.selectbox(
                        "演算子",
                        ["AND", "OR"],
                        index=0 if filter_item["operator"] == "AND" else 1,
                        key=f"filter_operator_{i}",
                        label_visibility="collapsed",
                        on_change=update_filter_operator,
                        args=(i,)
                    )
            with col_kw:
                st.text_input(
                    "キーワード",
                    value=filter_item["keyword"],
                    key=f"filter_keyword_{i}",
                    label_visibility="collapsed",
                    on_change=update_filter_keyword,
                    args=(i,)
                )
            with col_btn:
                if len(st.session_state.filters_keyword_page) > 1:
                    st.button("削除", key=f"remove_filter_{i}", on_click=remove_filter, args=(i,))
                else:
                    st.write("")

        st.button("フィルタ追加", on_click=add_filter, key="add_filter_button_keyword_page")
        st.markdown("---")

        filtered_df = df_source.copy()
        if not df_source.empty:
            if st.session_state.filters_keyword_page:
                current_filter_series = None
                
                first_condition_keyword = st.session_state.filters_keyword_page[0]['keyword'].strip()
                if first_condition_keyword:
                    first_regex = convert_wildcard_to_regex(first_condition_keyword)
                    current_filter_series = df_source['Message'].str.contains(first_regex, case=False, na=False, regex=True)
                else:
                    current_filter_series = pd.Series([True] * len(df_source), index=df_source.index)
                    
                for i in range(1, len(st.session_state.filters_keyword_page)):
                    condition = st.session_state.filters_keyword_page[i]
                    keyword = condition['keyword'].strip()
                    operator = condition['operator']
                    if not keyword:
                        continue

                    regex_keyword = convert_wildcard_to_regex(keyword)
                    current_condition = df_source['Message'].str.contains(regex_keyword, case=False, na=False, regex=True)

                    if operator == "AND":
                        current_filter_series = current_filter_series & current_condition
                    elif operator == "OR":
                        current_filter_series = current_filter_series | current_condition
                
                if current_filter_series is not None:
                    filtered_df = df_source[current_filter_series]
                else:
                    filtered_df = pd.DataFrame()
                    
            else:
                filtered_df = df_source
        else:
            filtered_df = pd.DataFrame()
        
        st.subheader("表示設定")
        max_rows = st.slider("表示する最大行数", 100, 1000000, 2000)

        st.subheader("フィルタリング結果")
        if not filtered_df.empty:
            st.write(f"表示中のログ数: {len(filtered_df)}行")
            
            if len(filtered_df) > max_rows:
                st.info(f"上位 {max_rows} 行のみ表示しています。")

            st.dataframe(filtered_df.tail(max_rows), use_container_width=True, height=1000)

            csv_data = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="表示中のデータフレームをCSVでダウンロード",
                data=csv_data,
                file_name='filtered_syslog_data.csv',
                mime='text/csv',
                key="download_filtered_output_csv_keyword_page"
            )
        else:
            st.info("表示するログがありません。フィルタリング条件を確認してください。")
    else:
        st.warning("ログデータが読み込まれていません。「データ読み込み」ページでファイルをアップロードしてください。")