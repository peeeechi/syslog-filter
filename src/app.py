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
# from src.app_pages import existing_filter_page, datetime_extract_page, about_page, upload_data_page, timeline_diagram_page, datetime_spec_page # 変更前
from src.app_pages import existing_filter_page, datetime_extract_page, about_page, upload_data_page, datetime_spec_page # 変更後 (timeline_diagram_page を削除)

st.set_page_config(layout="wide")

# --- ナビゲーションの状態を管理するSession State ---
if 'current_page' not in st.session_state:
    st.session_state.current_page = "data_upload"
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()
if 'df_filtered' not in st.session_state:
    st.session_state.df_filtered = pd.DataFrame()
if 'global_temp_dir' not in st.session_state:
    st.session_state.global_temp_dir = None
if 'is_returning_from_top_button' not in st.session_state:
    st.session_state.is_returning_from_top_button = False


# --- サイドバーのUI ---
st.sidebar.title("Syslog Filter App")
st.sidebar.markdown("---")

if st.sidebar.button(":information_source: このアプリケーションについて"):
    st.session_state.current_page = "about"
st.sidebar.markdown("---")

CLEANUP_ROOT_DIR = "temp_syslog_upload"
if st.sidebar.button(":wastebasket: 一時ファイルをクリーンアップ (全て削除)"):
    full_cleanup_path = os.path.abspath(CLEANUP_ROOT_DIR)
    print(f"DEBUG: クリーンアップを試行します。対象ディレクトリ: {full_cleanup_path}")
    if os.path.exists(full_cleanup_path):
        try:
            shutil.rmtree(full_cleanup_path)
            st.session_state.global_temp_dir = None
            st.session_state.df = pd.DataFrame()
            st.session_state.df_filtered = pd.DataFrame()
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
col_main_header, col_nav_button, col_top_button = st.columns([3, 1, 1])
with col_main_header:
    st.title("Syslog Filter Application")
with col_nav_button:
    # 日時指定ページとデータ読み込みページ以外でボタンを表示
    if not st.session_state.df.empty and st.session_state.current_page != "datetime_spec" and st.session_state.current_page != "data_upload":
        if st.button(":calendar: 日時指定ページへ", key="nav_to_datetime_spec_btn_top"):
            st.session_state.current_page = "datetime_spec"
            st.rerun()
with col_top_button:
    if st.session_state.current_page != "data_upload":
        if st.button(":house: トップページへ戻る"):
            st.session_state.current_page = "data_upload"
            st.session_state.is_returning_from_top_button = True
            st.rerun()

# --- ステップインジケーター ---
step1_color = "green" if st.session_state.current_page == "data_upload" else "gray"
step2_color = "green" if st.session_state.current_page == "datetime_spec" else "gray"
# step3_color = "green" if st.session_state.current_page in ["keyword_filter", "timeline_diagram"] else "gray" # 変更前
step3_color = "green" if st.session_state.current_page == "keyword_filter" else "gray" # 変更後 (timeline_diagram を削除)

st.markdown(
    f"<h3><span style='color: {step1_color};'>1. データ読み込み</span> > <span style='color: {step2_color};'>2. 日時指定・抽出</span> > <span style='color: {step3_color};'>3. ログ分析</span></h3>",
    unsafe_allow_html=True
)
st.markdown("---")


# ルーティングロジック
if st.session_state.df.empty and st.session_state.current_page != "about":
    st.warning("ログデータを読み込むまで、他の機能は選択できません。")
    st.session_state.current_page = "data_upload"
    upload_data_page.run()
elif st.session_state.current_page == "datetime_spec":
    datetime_spec_page.run()
elif st.session_state.current_page == "keyword_filter":
    existing_filter_page.run()
# elif st.session_state.current_page == "timeline_diagram": # 変更前
#     timeline_diagram_page.run() # 変更前
elif st.session_state.current_page == "about":
    about_page.run()
else:
    upload_data_page.run()