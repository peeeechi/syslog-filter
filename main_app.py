# main_app.py
import streamlit as st
from app_pages import existing_filter_page, datetime_extract_page, about_page, upload_data_page # upload_data_page を追加
import os
import shutil
from datetime import datetime

st.set_page_config(layout="wide")

# --- ナビゲーション ---
st.sidebar.title("Syslog Filter App")
st.sidebar.markdown("---")

# メニュー選択
selection = st.sidebar.radio(
    "メニューを選択",
    ["データ読み込み", "キーワードフィルタリング", "日付/時刻抽出", "このアプリケーションについて"] # 「データ読み込み」を追加
)

# --- ページ表示ロジック ---
if selection == "データ読み込み": # 新しいページを追加
    upload_data_page.run()
elif selection == "キーワードフィルタリング":
    existing_filter_page.run()
elif selection == "日付/時刻抽出":
    datetime_extract_page.run()
elif selection == "このアプリケーションについて":
    about_page.run()

# --- 一時ファイル管理 (共通) ---
CLEANUP_ROOT_DIR = "temp_syslog_upload" # クリーンアップ対象のルートディレクトリ

st.sidebar.markdown("---")
if st.sidebar.button("一時ファイルをクリーンアップ (全て削除)"):
    full_cleanup_path = os.path.abspath(CLEANUP_ROOT_DIR)
    print(f"DEBUG: クリーンアップを試行します。対象ディレクトリ: {full_cleanup_path}")

    if os.path.exists(full_cleanup_path):
        try:
            shutil.rmtree(full_cleanup_path)
            
            # セッションステートに関連するデータをクリア
            st.session_state.global_temp_dir = None
            st.session_state.df = None
            if 'found_log_files' in st.session_state:
                del st.session_state.found_log_files
            
            st.rerun()
            st.sidebar.success(f"一時ディレクトリ '{CLEANUP_ROOT_DIR}' と関連するログデータを全て削除しました。")
            print(f"DEBUG: ディレクトリ '{full_cleanup_path}' は正常に削除されました。")
        except OSError as e:
            st.sidebar.error(f"クリーンアップ中にエラーが発生しました: {e}。ディレクトリ '{CLEANUP_ROOT_DIR}' のファイルが使用中か、権限が不足している可能性があります。手動で削除してください。")
            print(f"ERROR: ディレクトリ '{full_cleanup_path}' の削除中にエラーが発生しました: {e}")
        except Exception as e:
            st.sidebar.error(f"予期せぬエラーが発生しました: {e}。手動で '{CLEANUP_ROOT_DIR}' を削除してください。")
            print(f"ERROR: 予期せぬエラーが発生しました: {e}")
    else:
        st.sidebar.info(f"クリーンアップするディレクトリ '{CLEANUP_ROOT_DIR}' は存在しません。")
        print(f"DEBUG: ディレクトリ '{full_cleanup_path}' は存在しませんでした。")