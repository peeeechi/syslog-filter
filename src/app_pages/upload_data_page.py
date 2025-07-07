# src/app_pages/upload_data_page.py
import streamlit as st
import pandas as pd
import os
import shutil
from datetime import datetime

# utilsからヘルパー関数をインポート (変更)
from src.utils.file_handlers import extract_zip, decompress_zstd_files, get_log_files, load_logs_from_path # 変更後 (絶対パス)

def run():
    st.title("ログデータの読み込み")
    st.markdown("分析を開始するには、まずログファイルをアップロードしてください。")

    if 'df' not in st.session_state or st.session_state.df is None:
        st.session_state.df = pd.DataFrame()
    
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
            st.session_state.df = load_logs_from_path(uploaded_file)
            st.session_state.found_log_files = []

        uploaded_file = None 

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
        elif uploaded_file is not None and uploaded_file.name.endswith('.zip') and not st.session_state.found_log_files:
             st.warning("展開されたディレクトリ内に.logファイルが見つかりませんでした。")
        
        st.success("データの読み込みが完了しました。")
        st.markdown("他の分析ページに移動して、ログデータを操作してください。")

    else:
        if not st.session_state.df.empty:
            st.success(f"{len(st.session_state.df)}件のログデータが現在読み込まれています。")
            st.dataframe(st.session_state.df.head())
        else:
            st.info("ログファイルがまだ読み込まれていません。")