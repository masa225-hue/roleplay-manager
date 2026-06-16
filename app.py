import os
import base64
from datetime import datetime
from pathlib import Path

import anthropic
import streamlit as st

PROMPT_PATH = Path(__file__).parent / "prompts" / "analysis.txt"


def get_api_key() -> str:
    # Streamlit Cloud の Secrets → ローカルの環境変数の順で取得
    return st.secrets.get("ANTHROPIC_API_KEY", os.getenv("ANTHROPIC_API_KEY", ""))


def get_analysis_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def transcribe_and_analyze(audio_bytes: bytes) -> tuple[str, str]:
    client = anthropic.Anthropic(api_key=get_api_key())
    audio_b64 = base64.standard_b64encode(audio_bytes).decode("utf-8")

    with st.spinner("文字起こし中…"):
        transcribe_resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "audio/wav",
                            "data": audio_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": "この音声を日本語でそのまま文字起こしてください。話者が複数いる場合は「話者A:」「話者B:」のように区別してください。",
                    },
                ],
            }],
        )
    transcript = transcribe_resp.content[0].text

    with st.spinner("分析・フィードバック生成中…"):
        analyze_resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=get_analysis_prompt(),
            messages=[{"role": "user", "content": f"【会話記録】\n{transcript}"}],
        )
    feedback = analyze_resp.content[0].text

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

# セッション情報
st.subheader("セッション情報")
col1, col2, col3 = st.columns(3)
with col1:
    date = st.date_input("実施日", value=datetime.today()).strftime("%Y-%m-%d")
with col2:
    manager = st.text_input("管理者名", placeholder="田中 花子")
with col3:
    participant = st.text_input("実施者名", placeholder="山田 太郎")

st.divider()

# 録音
st.subheader("録音")
audio = st.audio_input("マイクボタンを押して録音してください")

st.divider()

# 分析実行
if st.button("文字起こし・分析を実行", type="primary", disabled=audio is None):
    if not manager or not participant:
        st.error("管理者名と実施者名を入力してください")
    elif not get_api_key():
        st.error("ANTHROPIC_API_KEY が設定されていません")
    else:
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
