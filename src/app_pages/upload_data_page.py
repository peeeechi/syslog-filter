# src/app_pages/upload_data_page.py
import streamlit as st
import pandas as pd
import os
import shutil
from datetime import datetime

# utilsからヘルパー関数をインポート
from src.utils.file_handlers import extract_zip, decompress_zstd_files, get_log_files, load_logs_from_path

def run():
    st.title("ログデータの読み込み")
    st.markdown("分析を開始するには、まずログファイルをアップロードしてください。")

    if 'global_temp_dir' not in st.session_state or st.session_state.global_temp_dir is None:
        st.session_state.global_temp_dir = os.path.join("temp_syslog_upload", datetime.now().strftime("%Y%m%d%H%M%S_%f"))
        os.makedirs(st.session_state.global_temp_dir, exist_ok=True)

    uploaded_file = st.file_uploader("Syslogファイルをアップロードしてください (.log, .txt, .zip)", type=["log", "txt", "zip"], key="main_uploader")

    if uploaded_file is not None:
        if st.session_state.global_temp_dir and os.path.exists(st.session_state.global_temp_dir):
            shutil.rmtree(st.session_state.global_temp_dir)
            st.session_state.global_temp_dir = None

        st.session_state.global_temp_dir = os.path.join("temp_syslog_upload", datetime.now().strftime("%Y%m%d%H%M%S_%f"))
        os.makedirs(st.session_state.global_temp_dir, exist_ok=True)
        
        st.info(f"ファイルを処理中...一時ディレクトリ: {st.session_state.global_temp_dir}")

        if uploaded_file.name.endswith('.zip'):
            if extract_zip(uploaded_file, st.session_state.global_temp_dir):
                decompress_zstd_files(st.session_state.global_temp_dir)
                st.session_state.found_log_files = get_log_files(st.session_state.global_temp_dir)
            else:
                st.session_state.global_temp_dir = None
                st.session_state.found_log_files = []
        else:
            # 単一ファイルの直接アップロードの場合の処理
            # uploaded_file は BytesIO オブジェクトのように扱えるため、そのまま load_logs_from_path に渡す
            st.session_state.df = load_logs_from_path(uploaded_file)
            st.session_state.found_log_files = [] # 単一ファイルなので、リストは空でOK

        # zipの場合の処理
        if 'found_log_files' in st.session_state and st.session_state.found_log_files:
            if len(st.session_state.found_log_files) == 1:
                selected_log_file_path = st.session_state.found_log_files[0]
                st.info(f"単一のログファイル '{os.path.basename(selected_log_file_path)}' を自動選択しました。")
                st.session_state.df = load_logs_from_path(selected_log_file_path)
            else:
                st.subheader("複数のログファイルが見つかりました")
                selected_log_file_name = st.selectbox(
                    "分析するログファイルを選択してください:",
                    [os.path.basename(f) for f in st.session_state.found_log_files],
                    key="log_file_selector"
                )
                selected_log_file_path = next((f for f in st.session_state.found_log_files if os.path.basename(f) == selected_log_file_name), None)
                if selected_log_file_path:
                    st.session_state.df = load_logs_from_path(selected_log_file_path)
        elif uploaded_file.name.endswith('.zip') and not st.session_state.found_log_files:
             st.warning("展開されたディレクトリ内に.logファイルが見つかりませんでした。")
        
        st.success("データの読み込みが完了しました。")
        st.markdown("---")
        # データが正常にアップロードされた場合、is_returning_from_top_button フラグをリセット
        st.session_state.is_returning_from_top_button = False

    # データが既に読み込まれている場合の表示ロジック
    if not st.session_state.df.empty:
        st.success(f"{len(st.session_state.df)}件のログデータが現在読み込まれています。")
        
        display_df_head = st.session_state.df.head().copy()
        if 'Timestamp' in display_df_head.columns and pd.api.types.is_datetime64_any_dtype(display_df_head['Timestamp']):
            display_df_head['Timestamp'] = display_df_head['Timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S.%f')
        st.dataframe(display_df_head)
        
        st.markdown("---")

        # --- 修正箇所: データが読み込まれている場合に常にボタンを表示 ---
        st.subheader("分析ページに移動する")
        st.markdown("""
            <style>
            .nav-buttons-container .stButton>button {
                font-size: 1.2rem;
                padding: 15px 30px;
                width: 100%;
            }
            </style>
            <div class="nav-buttons-container">
            """, unsafe_allow_html=True)
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button(":calendar: 日時指定・抽出へ", key="nav_to_datetime_page_btn"):
                st.session_state.current_page = "datetime_spec"
                st.rerun()
        with col_btn2:
            if st.button(":mag: キーワードフィルタリングへ", key="nav_to_keyword_page_btn"):
                st.session_state.current_page = "keyword_filter"
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
        # -------------------------------------------------------------

        # データが正常にアップロードされた（または既に存在した）場合、自動遷移
        # ただし、トップページに戻るボタンからの遷移の場合は自動遷移しない
        if not st.session_state.get('is_returning_from_top_button', False):
            st.session_state.current_page = "datetime_spec"
            st.rerun()
        else:
            # is_returning_from_top_button フラグをリセットして、次回以降の自動遷移を有効にする
            st.session_state.is_returning_from_top_button = False

    else:
        st.info("ログファイルがまだ読み込まれていません。上記のアップローダーからファイルをアップロードしてください。")