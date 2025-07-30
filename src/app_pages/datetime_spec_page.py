# src/app_pages/datetime_spec_page.py
import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timedelta
import io
import csv
import pytz

def generate_hour_options():
    """00から23までの時間の選択肢を文字列で生成する"""
    return [f"{i:02d}" for i in range(24)]

def generate_minute_options():
    """00から59までの分の選択肢を文字列で生成する (1分単位)"""
    return [f"{i:02d}" for i in range(60)]

def run():
    st.title("日時によるログの絞り込み")
    st.write("ステップ3の分析ページに進む前に、ログの期間を絞り込んでください。")

    df_source = st.session_state.df if 'df' in st.session_state and st.session_state.df is not None else pd.DataFrame()

    if df_source.empty:
        st.warning("ログデータが読み込まれていません。「データ読み込み」ページでファイルをアップロードしてください。")
        st.session_state.current_page = "data_upload"
        st.rerun()
        return

    st.write(f"元のログの行数: {len(df_source)}行")
    st.subheader("絞り込み設定")

    if not df_source['Timestamp'].empty and pd.api.types.is_datetime64_any_dtype(df_source['Timestamp']):
        min_date_available = df_source['Timestamp'].dt.date.min()
        max_date_available = df_source['Timestamp'].dt.date.max()
    else:
        min_date_available = date.today()
        max_date_available = date.today()
    
    if 'datetime_spec_conditions' in st.session_state:
        saved_conditions = st.session_state.datetime_spec_conditions
        default_start_date = saved_conditions.get("start_date", min_date_available)
        default_end_date = saved_conditions.get("end_date", max_date_available)
    else:
        default_start_date = min_date_available if pd.notna(min_date_available) else date.today()
        default_end_date = max_date_available if pd.notna(max_date_available) else date.today()

    if default_start_date < min_date_available:
        default_start_date = min_date_available
    if default_start_date > max_date_available:
        default_start_date = max_date_available
    if default_end_date > max_date_available:
        default_end_date = max_date_available
    if default_end_date < min_date_available:
        default_end_date = min_date_available
    
    col_date_start, col_date_end = st.columns(2)
    with col_date_start:
        start_date_selection = st.date_input(
            "開始日:",
            value=default_start_date,
            min_value=min_date_available,
            max_value=max_date_available,
            key="start_date_spec"
        )
    with col_date_end:
        end_date_selection = st.date_input(
            "終了日:",
            value=default_end_date,
            min_value=start_date_selection,
            max_value=max_date_available,
            key="end_date_spec"
        )

    if start_date_selection > end_date_selection:
        st.warning("開始日は終了日より前の日付にしてください。")
        
    hour_options = generate_hour_options()
    minute_options = generate_minute_options()
    
    if 'datetime_spec_conditions' in st.session_state:
        saved_conditions = st.session_state.datetime_spec_conditions
        start_hour_index = hour_options.index(saved_conditions.get("start_hour", hour_options[0])) if saved_conditions.get("start_hour") in hour_options else 0
        start_minute_index = minute_options.index(saved_conditions.get("start_minute", minute_options[0])) if saved_conditions.get("start_minute") in minute_options else 0
        end_hour_index = hour_options.index(saved_conditions.get("end_hour", hour_options[-1])) if saved_conditions.get("end_hour") in hour_options else len(hour_options)-1
        end_minute_index = minute_options.index(saved_conditions.get("end_minute", minute_options[-1])) if saved_conditions.get("end_minute") in minute_options else len(minute_options)-1
    else:
        start_hour_index = 0
        start_minute_index = 0
        end_hour_index = len(hour_options) - 1
        end_minute_index = len(minute_options) - 1

    st.markdown("**開始時刻:**")
    col_start_h, col_start_m = st.columns(2)
    with col_start_h:
        selected_start_hour_str = st.selectbox("時", hour_options, index=start_hour_index, key="start_hour_spec", label_visibility="collapsed")
    with col_start_m:
        selected_start_minute_str = st.selectbox("分", minute_options, index=start_minute_index, key="start_minute_spec", label_visibility="collapsed")
    start_time_obj = datetime.strptime(f"{selected_start_hour_str}:{selected_start_minute_str}", '%H:%M').time()

    st.markdown("**終了時刻:**")
    col_end_h, col_end_m = st.columns(2)
    with col_end_h:
        selected_end_hour_str = st.selectbox("時", hour_options, index=end_hour_index, key="end_hour_spec", label_visibility="collapsed")
    with col_end_m:
        selected_end_minute_str = st.selectbox("分", minute_options, index=end_minute_index, key="end_minute_spec", label_visibility="collapsed")
    end_time_obj = datetime.strptime(f"{selected_end_hour_str}:{selected_end_minute_str}", '%H:%M').time()

    if st.button("絞り込みを実行", key="filter_datetime_button"):
        with st.spinner('ログデータを絞り込み中...'):
            filtered_df = df_source.copy()
            
            start_datetime_full_naive = datetime.combine(start_date_selection, start_time_obj)
            # --- 修正箇所: timedelta の部分を再度追加 ---
            end_datetime_full_naive = datetime.combine(end_date_selection, end_time_obj) + timedelta(seconds=59, microseconds=999999)
            # -----------------------------------------------
            
            if not df_source.empty and 'Timestamp' in df_source.columns and pd.api.types.is_datetime64_any_dtype(df_source['Timestamp']):
                df_tz = df_source['Timestamp'].dt.tz
                
                if df_tz:
                    try:
                        tz_name = str(df_tz)
                        target_timezone = pytz.timezone(tz_name)
                        start_datetime_full = target_timezone.localize(start_datetime_full_naive)
                        end_datetime_inclusive = target_timezone.localize(end_datetime_full_naive)
                    except pytz.exceptions.UnknownTimeZoneError:
                        st.warning(f"不明なタイムゾーン: {tz_name} が検出されました。時刻フィルタリングはタイムゾーンを考慮せずに行われます。")
                        filtered_df['Timestamp'] = filtered_df['Timestamp'].dt.tz_localize(None)
                        start_datetime_full = start_datetime_full_naive
                        end_datetime_inclusive = end_datetime_full_naive
                else:
                    start_datetime_full = start_datetime_full_naive
                    end_datetime_inclusive = end_datetime_full_naive
            else:
                start_datetime_full = start_datetime_full_naive
                end_datetime_inclusive = end_datetime_full_naive
            
            if 'Timestamp' in filtered_df.columns and pd.api.types.is_datetime64_any_dtype(filtered_df['Timestamp']):
                filtered_df = filtered_df[
                    (filtered_df['Timestamp'] >= start_datetime_full) &
                    (filtered_df['Timestamp'] <= end_datetime_inclusive)
                ]
            
            st.session_state.df_filtered = filtered_df
            
            st.session_state.datetime_spec_conditions = {
                "start_date": start_date_selection,
                "end_date": end_date_selection,
                "start_hour": selected_start_hour_str,
                "start_minute": selected_start_minute_str,
                "end_hour": selected_end_hour_str,
                "end_minute": selected_end_minute_str,
                "filtered_count": len(filtered_df)
            }
            
            st.success(f"{len(st.session_state.df_filtered)}件のログを絞り込みました。")
            st.rerun()

    if 'df_filtered' in st.session_state and st.session_state.df_filtered is not None:
        st.subheader("絞り込み結果の確認")
        st.write(f"絞り込み後のログの行数: {len(st.session_state.df_filtered)}行")
        
        if not st.session_state.df_filtered.empty:
            display_df_filtered = st.session_state.df_filtered.copy()
            if 'Timestamp' in display_df_filtered.columns and pd.api.types.is_datetime64_any_dtype(display_df_filtered['Timestamp']):
                display_df_filtered['Timestamp'] = display_df_filtered['Timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S.%f')
            
            total_rows = len(display_df_filtered)
            if total_rows > 6:
                st.dataframe(display_df_filtered.head(3), use_container_width=True)
                st.write(f"中略（さらに {total_rows - 6} 行のログがあります）")
                st.dataframe(display_df_filtered.tail(3), use_container_width=True)
            else:
                st.dataframe(display_df_filtered, use_container_width=True)
            
            st.markdown("---")

            download_format = st.radio("ダウンロード形式を選択", ("CSV", "LOG"), key="download_spec_format")

            if download_format == "CSV":
                csv_data_datetime = st.session_state.df_filtered.to_csv(
                    index=False, 
                    quoting=csv.QUOTE_ALL,
                    escapechar='\\'
                ).encode('utf-8')
                st.download_button(
                    label="抽出ログをCSVでダウンロード",
                    data=csv_data_datetime,
                    file_name="datetime_filtered.csv",
                    mime="text/csv",
                    key="download_spec_csv"
                )
            else: # LOG形式
                log_lines_output = []
                for _, row in st.session_state.df_filtered.iterrows():
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
                    file_name="datetime_filtered.log",
                    mime="text/plain",
                    key="download_spec_log"
                )

        else:
            st.info("指定された条件に一致するログは見つかりませんでした。")
        
        st.markdown("---")
        st.subheader("次のステップへ")
        col_btn1, = st.columns(1)
        with col_btn1:
            if st.button("キーワードフィルタリングへ", key="nav_to_keyword_from_spec"):
                st.session_state.current_page = "keyword_filter"
                st.rerun()