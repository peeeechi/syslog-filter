# src/app_pages/datetime_extract_page.py
import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta, date, time # date もインポート
import shutil
import io

# utilsからヘルパー関数をインポート
from src.utils.file_handlers import extract_zip, decompress_zstd_files, get_log_files, load_logs_from_path
from src.utils.log_parser_utils import SYSLOG_PATTERN

# --- 時間選択肢の生成ヘルパー関数 ---
def generate_time_options(interval_minutes=5):
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

    df_to_extract = st.session_state.df if 'df' in st.session_state and st.session_state.df is not None else pd.DataFrame()

    if not df_to_extract.empty:
        st.write(f"元のログの行数: {len(df_to_extract)}行")

        st.subheader("日付と時刻でログを抽出")

        # 利用可能な日付の範囲を特定
        min_date_available = df_to_extract['Timestamp'].dt.date.min() if not df_to_extract['Timestamp'].empty else date.today()
        max_date_available = df_to_extract['Timestamp'].dt.date.max() if not df_to_extract['Timestamp'].empty else date.today()

        # 日付選択ウィジェットの初期値を設定
        # データが読み込まれていない場合は今日の日付、読み込まれている場合は最小/最大日付
        default_start_date = min_date_available if not df_to_extract.empty and pd.notna(min_date_available) else date.today()
        default_end_date = max_date_available if not df_to_extract.empty and pd.notna(max_date_available) else date.today()

        col_date_start, col_date_end = st.columns(2)
        with col_date_start:
            start_date_selection = st.date_input(
                "開始日:",
                value=default_start_date,
                min_value=min_date_available,
                max_value=max_date_available if pd.notna(max_date_available) else date.today(),
                key="start_date_input"
            )
        with col_date_end:
            end_date_selection = st.date_input(
                "終了日:",
                value=default_end_date,
                min_value=start_date_selection, # 終了日は開始日より前にはできない
                max_value=max_date_available if pd.notna(max_date_available) else date.today(),
                key="end_date_input"
            )

        if start_date_selection > end_date_selection:
            st.warning("開始日は終了日より前の日付にしてください。")
            # ここで処理を中断するか、end_date_selectionをstart_date_selectionに強制的に合わせることも可能
            # 例: end_date_selection = start_date_selection
            # 今回は警告のみで続行し、フィルタリング結果が空になることを期待

        time_options = generate_time_options(5)
        col_time_start, col_time_end = st.columns(2)
        with col_time_start:
            selected_start_time_str = st.selectbox("開始時刻 (HH:MM):", time_options, index=0, key="start_time_select")
            start_time = datetime.strptime(selected_start_time_str, '%H:%M').time()

        with col_time_end:
            selected_end_time_str = st.selectbox("終了時刻 (HH:MM):", time_options, index=len(time_options) - 1, key="end_time_select")
            end_time = datetime.strptime(selected_end_time_str, '%H:%M').time()

        date_time_filtered_df = df_to_extract.copy()

        # 日付範囲でフィルタリング
        if not df_to_extract.empty and 'Timestamp' in df_to_extract.columns and df_to_extract['Timestamp'].notna().any():
            date_time_filtered_df = date_time_filtered_df[
                (date_time_filtered_df['Timestamp'].dt.date >= start_date_selection) &
                (date_time_filtered_df['Timestamp'].dt.date <= end_date_selection)
            ]

        # 時刻でフィルタリング
        if start_time and end_time:
            date_time_filtered_df = date_time_filtered_df[
                (date_time_filtered_df['Timestamp'].notna()) &
                (date_time_filtered_df['Timestamp'].dt.time >= start_time) &
                (date_time_filtered_df['Timestamp'].dt.time <= end_time)
            ]

        st.subheader("表示設定")
        max_display_rows = st.slider("表示する最大行数", 100, 1000000, 2000, key="max_display_rows_slider")

        st.subheader("抽出結果")

        if not date_time_filtered_df.empty:
            st.write(f"日付/時刻抽出されたログ数: {len(date_time_filtered_df)}行")
            
            display_df = date_time_filtered_df
            if len(date_time_filtered_df) > max_display_rows:
                display_df = date_time_filtered_df.tail(max_display_rows)
                st.info(f"上位 {max_display_rows} 行のみ表示しています。")

            st.dataframe(display_df, use_container_width=True, height=1000)
            
            download_format = st.radio("ダウンロード形式を選択", ("CSV", "LOG"), key="download_format_radio")

            # ファイル名に開始日と終了日を反映
            file_date_part_start = start_date_selection.strftime('%Y%m%d')
            file_date_part_end = end_date_selection.strftime('%Y%m%d')
            
            if download_format == "CSV":
                csv_data_datetime = date_time_filtered_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="抽出ログをCSVでダウンロード",
                    data=csv_data_datetime,
                    file_name=f"extracted_logs_{file_date_part_start}-{file_date_part_end}_{selected_start_time_str.replace(':', '')}-{selected_end_time_str.replace(':', '')}.csv",
                    mime="text/csv",
                    key="download_datetime_filtered_csv"
                )
            else:
                log_lines_output = []
                for _, row in date_time_filtered_df.iterrows():
                    timestamp_str = row['Timestamp'].isoformat() if pd.notna(row['Timestamp']) else ""
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
                    file_name=f"extracted_logs_{file_date_part_start}-{file_date_part_end}_{selected_start_time_str.replace(':', '')}-{selected_end_time_str.replace(':', '')}.log",
                    mime="text/plain",
                    key="download_datetime_filtered_log"
                )
        else:
            st.info("指定された日付/時刻に一致するログが見つかりませんでした。")
    else:
        st.warning("ログデータが読み込まれていません。「データ読み込み」ページでファイルをアップロードしてください。")