import os
from datetime import datetime
from pathlib import Path

from google import genai
from google.genai import types
import streamlit as st

PROMPT_PATH = Path(__file__).parent / "prompts" / "analysis.txt"


def get_api_key() -> str:
    return st.secrets.get("GOOGLE_API_KEY", os.getenv("GOOGLE_API_KEY", ""))


def get_analysis_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def transcribe_and_analyze(audio_bytes: bytes) -> tuple[str, str]:
    client = genai.Client(api_key=get_api_key())

    with st.spinner("文字起こし中…"):
        transcribe_resp = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[
                types.Part.from_bytes(data=audio_bytes, mime_type="audio/webm"),
                "この音声を日本語でそのまま文字起こしてください。話者が複数いる場合は「話者A:」「話者B:」のように区別してください。",
            ],
        )
    transcript = transcribe_resp.text

    with st.spinner("分析・フィードバック生成中…"):
        analyze_resp = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=f"{get_analysis_prompt()}\n\n【会話記録】\n{transcript}",
        )
    feedback = analyze_resp.text

    return transcript, feedback


def save_to_sheets(date: str, manager: str, participant: str, transcript: str, feedback: str) -> bool:
    sheet_id = st.secrets.get("GOOGLE_SHEET_ID", os.getenv("GOOGLE_SHEET_ID", ""))
    sa_json = st.secrets.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")

    if not sheet_id or not sa_json:
        return False

    try:
        import json
        import gspread
        from google.oauth2.service_account import Credentials

        info = json.loads(sa_json)
        creds = Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        gc = gspread.authorize(creds)
        ws = gc.open_by_key(sheet_id).sheet1
        ws.append_row([
            date,
            manager,
            participant,
            datetime.now().strftime("%H:%M:%S"),
            transcript,
            feedback,
        ])
        return True
    except Exception:
        return False


# ---- UI ----

st.set_page_config(page_title="ロールプレイ管理ツール", page_icon="🎙️", layout="centered")
st.title("ロールプレイ管理ツール")

st.subheader("セッション情報")
col1, col2, col3 = st.columns(3)
with col1:
    date = st.date_input("実施日", value=datetime.today()).strftime("%Y-%m-%d")
with col2:
    manager = st.text_input("管理者名", placeholder="田中 花子")
with col3:
    participant = st.text_input("実施者名", placeholder="山田 太郎")

st.divider()

st.subheader("録音")
audio = st.audio_input("マイクボタンを押して録音してください")

st.divider()

if st.button("文字起こし・分析を実行", type="primary", disabled=audio is None):
    if not manager or not participant:
        st.error("管理者名と実施者名を入力してください")
    elif not get_api_key():
        st.error("GOOGLE_API_KEY が設定されていません")
    else:
        try:
            transcript, feedback = transcribe_and_analyze(audio.read())
            sheets_saved = save_to_sheets(date, manager, participant, transcript, feedback)

            st.subheader("文字起こし")
            st.text_area("", value=transcript, height=200, label_visibility="collapsed")

            st.subheader("フィードバック")
            st.markdown(feedback)

            if sheets_saved:
                st.success("スプレッドシートに保存しました")
            else:
                st.info("スプレッドシートは未設定です（任意）")
        except Exception as e:
            st.error(f"エラーが発生しました:\n\n{type(e).__name__}: {e}")
