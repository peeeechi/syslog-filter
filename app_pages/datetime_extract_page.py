# app_pages/datetime_extract_page.py
import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta, time
import shutil
import io

# utilsからヘルパー関数をインポート
from utils.file_handlers import extract_zip, decompress_zstd_files, get_log_files, load_logs_from_path
from utils.log_parser_utils import SYSLOG_PATTERN # ログ再構築用にSYSLOG_PATTERNもインポート

# --- 時間選択肢の生成ヘルパー関数 ---
def generate_time_options(interval_minutes=5):
    """00:00から23:55まで指定された分刻みの時間オプションを生成する"""
    times = []
    start = datetime.strptime("00:00", "%H:%M")
    end = datetime.strptime("23:59", "%H:%M")
    current = start
    while current <= end:
        times.append(current.strftime("%H:%M"))
        current += timedelta(minutes=interval_minutes)
    return times

# --- アプリケーション本体 ---
def run():
    st.title("日付と時刻でログを抽出")

    # ログデータの取得 (st.session_state.df を利用)
    df_to_extract = st.session_state.df if 'df' in st.session_state and st.session_state.df is not None else pd.DataFrame()

    if not df_to_extract.empty:
        # --- 元のログ行数の表示 (existing_filter_page.py と同様) ---
        st.write(f"元のログの行数: {len(df_to_extract)}行")

        st.subheader("日付と時刻でログを抽出")

        # --- 日付選択 (カレンダーからリストへ変更) ---
        available_dates = sorted(df_to_extract['Timestamp'].dt.date.dropna().unique())
        target_date = None
        if available_dates:
            formatted_dates = [d.strftime('%Y-%m-%d') for d in available_dates]
            selected_date_str = st.selectbox("抽出する日付を選択:", ["選択してください"] + formatted_dates, index=0)
            if selected_date_str != "選択してください":
                target_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        else:
            st.warning("ログデータから有効な日付が見つかりませんでした。")

        # --- 時間選択 (5分刻みへ変更) ---
        time_options = generate_time_options(5)
        col_time_start, col_time_end = st.columns(2)
        with col_time_start:
            selected_start_time_str = st.selectbox("開始時刻 (HH:MM):", time_options, index=0)
            start_time = datetime.strptime(selected_start_time_str, '%H:%M').time()

        with col_time_end:
            selected_end_time_str = st.selectbox("終了時刻 (HH:MM):", time_options, index=len(time_options) - 1)
            end_time = datetime.strptime(selected_end_time_str, '%H:%M').time()

        date_time_filtered_df = df_to_extract.copy()

        # --- フィルタリングロジック ---
        if target_date:
            date_time_filtered_df = date_time_filtered_df[
                (date_time_filtered_df['Timestamp'].notna()) &
                (date_time_filtered_df['Timestamp'].dt.date == target_date)
            ]

        if start_time and end_time:
            date_time_filtered_df = date_time_filtered_df[
                (date_time_filtered_df['Timestamp'].notna()) &
                (date_time_filtered_df['Timestamp'].dt.time >= start_time) &
                (date_time_filtered_df['Timestamp'].dt.time <= end_time)
            ]

        # --- 表示設定 (existing_filter_page.py と同様) ---
        st.subheader("表示設定")
        # スライダーの範囲とデフォルト値を existing_filter_page.py (元のapp.py) と合わせる
        max_display_rows = st.slider("表示する最大行数", 100, 1000000, 2000)

        st.subheader("抽出結果") # サブヘッダーを「抽出結果」に変更

        if not date_time_filtered_df.empty:
            st.write(f"日付/時刻抽出されたログ数: {len(date_time_filtered_df)}行")
            
            display_df = date_time_filtered_df # display_df を定義
            # --- 「上位 N 行のみ表示しています。」メッセージの追加 (existing_filter_page.py と同様) ---
            if len(date_time_filtered_df) > max_display_rows:
                display_df = date_time_filtered_df.tail(max_display_rows) # 最新のN行を表示
                st.info(f"上位 {max_display_rows} 行のみ表示しています。")

            # --- st.dataframe の引数を existing_filter_page.py と同様に設定 ---
            st.dataframe(display_df, use_container_width=True, height=1000)
            
            # --- ダウンロード形式の選択 (CSV or LOG) ---
            download_format = st.radio("ダウンロード形式を選択", ("CSV", "LOG"))

            file_date_part = target_date.strftime('%Y%m%d') if target_date else 'nodaydate'

            if download_format == "CSV":
                csv_data_datetime = date_time_filtered_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="抽出ログをCSVでダウンロード",
                    data=csv_data_datetime,
                    file_name=f"extracted_logs_{file_date_part}_{selected_start_time_str.replace(':', '')}-{selected_end_time_str.replace(':', '')}.csv",
                    mime="text/csv",
                    key="download_datetime_filtered_csv"
                )
            else: # LOG形式
                log_lines_output = []
                for _, row in date_time_filtered_df.iterrows():
                    timestamp_str = row['Timestamp'].isoformat() if row['Timestamp'] else ""
                    hostname_str = str(row['Hostname']) if pd.notna(row['Hostname']) else "-"
                    app_name_str = str(row['AppName']) if pd.notna(row['AppName']) else "-"
                    pid_str = f"[{int(row['PID'])}]" if pd.notna(row['PID']) else ""
                    message_str = str(row['Message']) if pd.notna(row['Message']) else ""
                    
                    log_line = f"{timestamp_str} {hostname_str} {app_name_str}{pid_str}: {message_str}"
                    log_lines_output.append(log_line)
                
                log_data_datetime = "\n".join(log_lines_output).encode('utf-8')
                st.download_button(
                    label="抽出ログをLOGでダウンロード",
                    data=log_data_datetime,
                    file_name=f"extracted_logs_{file_date_part}_{selected_start_time_str.replace(':', '')}-{selected_end_time_str.replace(':', '')}.log",
                    mime="text/plain",
                    key="download_datetime_filtered_log"
                )
        else:
            st.info("指定された日付/時刻に一致するログが見つかりませんでした。")
    else:
        st.warning("ログデータが読み込まれていません。「データ読み込み」ページでファイルをアップロードしてください。")