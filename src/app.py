# src/app.py
import sys
import os
import streamlit as st
import shutil
from datetime import datetime
import pandas as pd

# プロジェクトのルートディレクトリをsys.pathに追加
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if project_root not in sys.path:
    sys.path.append(project_root)

# 各ページをインポート
from src.app_pages import existing_filter_page, datetime_extract_page, about_page, upload_data_page

st.set_page_config(layout="wide")

# --- ナビゲーションの状態を管理するSession State ---
if 'current_page' not in st.session_state:
    st.session_state.current_page = "data_upload"
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()
if 'global_temp_dir' not in st.session_state:
    st.session_state.global_temp_dir = None


# --- サイドバーのUI ---
st.sidebar.title("Syslog Filter App")
st.sidebar.markdown("---")

# 「このアプリケーションについて」ボタン
if st.sidebar.button("このアプリケーションについて"):
    st.session_state.current_page = "about"
st.sidebar.markdown("---")

# 「一時ファイルをクリーンアップ」ボタン
CLEANUP_ROOT_DIR = "temp_syslog_upload"
if st.sidebar.button("一時ファイルをクリーンアップ (全て削除)"):
    full_cleanup_path = os.path.abspath(CLEANUP_ROOT_DIR)
    print(f"DEBUG: クリーンアップを試行します。対象ディレクトリ: {full_cleanup_path}")
    if os.path.exists(full_cleanup_path):
        try:
            shutil.rmtree(full_cleanup_path)
            st.session_state.global_temp_dir = None
            st.session_state.df = pd.DataFrame()
            if 'found_log_files' in st.session_state:
                del st.session_state.found_log_files
            st.session_state.current_page = "data_upload"
            st.rerun()
            st.sidebar.success(f"一時ディレクトリ '{CLEANUP_ROOT_DIR}' と関連するログデータを全て削除しました。")
            print(f"DEBUG: ディレクトリ '{full_cleanup_path}' は正常に削除されました。")
        except OSError as e:
            st.sidebar.error(f"クリーンアップ中にエラーが発生しました: {e}。手動で '{CLEANUP_ROOT_DIR}' を削除してください。")
            print(f"ERROR: ディレクトリ '{full_cleanup_path}' の削除中にエラーが発生しました: {e}")
        except Exception as e:
            st.sidebar.error(f"予期せぬエラーが発生しました: {e}。手動で '{CLEANUP_ROOT_DIR}' を削除してください。")
            print(f"ERROR: 予期せぬエラーが発生しました: {e}")
    else:
        st.sidebar.info(f"クリーンアップするディレクトリ '{CLEANUP_ROOT_DIR}' は存在しません。")
        print(f"DEBUG: ディレクトリ '{full_cleanup_path}' は存在しませんでした。")

# --- メインコンテンツのUIとルーティング ---
col_main_header, col_top_button = st.columns([4, 1])
with col_main_header:
    st.title("Syslog Filter Application")
with col_top_button:
    # データ読み込みページ以外でボタンを表示
    if st.session_state.current_page != "data_upload":
        if st.button(":house: データ読み込みページへ戻る"):
            st.session_state.current_page = "data_upload"
            st.rerun()

# --- ステップインジケーター ---
if st.session_state.df.empty:
    st.markdown("<h3><span style='color: green;'>1. データ読み込み</span> > <span style='color: gray;'>2. ログ分析</span></h3>", unsafe_allow_html=True)
else:
    st.markdown("<h3><span style='color: gray;'>1. データ読み込み</span> > <span style='color: green;'>2. ログ分析</span></h3>", unsafe_allow_html=True)
st.markdown("---")


# データが読み込まれていない場合は強制的にデータ読み込みページを表示
if st.session_state.df.empty and st.session_state.current_page != "about":
    st.warning("ログデータを読み込むまで、他の機能は選択できません。")
    st.session_state.current_page = "data_upload"

# --- ページ表示ロジック ---
if st.session_state.current_page == "data_upload":
    upload_data_page.run()
elif st.session_state.current_page == "keyword_filter":
    if st.session_state.df.empty:
        st.session_state.current_page = "data_upload"
        st.rerun()
    else:
        existing_filter_page.run()
elif st.session_state.current_page == "datetime_extract":
    if st.session_state.df.empty:
        st.session_state.current_page = "data_upload"
        st.rerun()
    else:
        datetime_extract_page.run()
elif st.session_state.current_page == "about":
    about_page.run()