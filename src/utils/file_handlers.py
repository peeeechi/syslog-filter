# src/utils/file_handlers.py
import streamlit as st
import zipfile
import os
import shutil
import zstandard as zstd
import io
import pandas as pd
from datetime import datetime

# utilsからparse_syslog_lineをインポート (変更)
# from .log_parser_utils import parse_syslog_line # 変更前
from .log_parser_utils import parse_syslog_line # 変更後 (すでに相対パス)

def extract_zip(uploaded_file, extract_to):
    try:
        with zipfile.ZipFile(io.BytesIO(uploaded_file.getvalue()), 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        st.success(f"ZIPファイルを '{extract_to}' に展開しました。")
        return True
    except zipfile.BadZipFile:
        st.error("不正なZIPファイルです。")
        return False
    except Exception as e:
        st.error(f"ZIPファイルの展開中にエラーが発生しました: {e}")
        return False

def decompress_zstd_files(directory):
    decompressed_count = 0
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.zst'):
                zstd_file_path = os.path.join(root, file)
                output_file_path = zstd_file_path.replace('.zst', '')
                try:
                    with open(zstd_file_path, 'rb') as f_in:
                        dctx = zstd.ZstdDecompressor()
                        with open(output_file_path, 'wb') as f_out:
                            dctx.copy_stream(f_in, f_out)
                    decompressed_count += 1
                    os.remove(zstd_file_path)
                except Exception as e:
                    st.warning(f"'{file}' (.zst) の展開中にエラーが発生しました: {e}")
    if decompressed_count > 0:
        st.success(f"{decompressed_count}個の.zstファイルを展開しました。")
    return decompressed_count

def get_log_files(directory):
    log_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.log'):
                log_files.append(os.path.join(root, file))
    return log_files

def load_logs_from_path(log_source):
    parsed_logs = []
    
    if isinstance(log_source, str):
        try:
            with open(log_source, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    parsed_data = parse_syslog_line(line)
                    if parsed_data:
                        parsed_logs.append(parsed_data)
            st.success(f"'{os.path.basename(log_source)}' から {len(parsed_logs)}件のログを読み込みました。")
        except Exception as e:
            st.error(f"ログファイルの読み込み中にエラーが発生しました ('{os.path.basename(log_source)}'): {e}")
            return pd.DataFrame()
    else:
        try:
            string_io = io.StringIO(log_source.getvalue().decode("utf-8", errors='ignore'))
            for line in string_io.readlines():
                parsed_data = parse_syslog_line(line)
                if parsed_data:
                    parsed_logs.append(parsed_data)
            st.success(f"'{log_source.name}' から {len(parsed_logs)}件のログを読み込みました。")
        except Exception as e:
            st.error(f"ログファイルの読み込み中にエラーが発生しました ('{log_source.name}'): {e}")
            return pd.DataFrame()
            
    if parsed_logs:
        df = pd.DataFrame(parsed_logs)
        return df
    else:
        st.warning("有効なSyslogエントリが見つかりませんでした。")
        return pd.DataFrame()