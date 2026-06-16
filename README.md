# ロールプレイ管理ツール

サーバー不要のデスクトップアプリ。

## セットアップ

### 1. パッケージのインストール
```bash
cd ~/roleplay-manager
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. APIキーの設定
```bash
cp .env.example .env
# .envを開いてANTHROPIC_API_KEYを入力
```

### 3. 起動
```bash
source venv/bin/activate
python main.py
```

## Google Sheets連携（任意）
1. Google Cloud Console でサービスアカウントを作成、JSONキーをダウンロード
2. `service_account.json` としてこのフォルダに保存
3. スプレッドシートをそのアカウントのメールに共有（編集者）
4. `.env` の `GOOGLE_SHEET_ID` にスプレッドシートIDを設定

スプレッドシート1行目のヘッダー: `実施日 | 管理者 | 実施者 | 時刻 | 文字起こし | フィードバック`

## 分析プロンプトのカスタマイズ
`prompts/analysis.txt` を編集するだけ。
