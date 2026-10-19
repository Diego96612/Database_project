# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案概觀

這是 **2026 年上半年東吳大學資料科學系 LINE Bot 進階課程**的教學範例集。整個 repo 不是單一應用，而是**多個獨立、可單獨執行的 LINE Bot 範例檔**，每一支對應課程的一個進度，從最簡單的單輪對話，逐步加上 system prompt、logging、多輪對話、Google Search、圖片／影片處理，以及 OpenAI 替代實作。

部署目標是 **Hugging Face Spaces（Docker SDK）**，README 的 frontmatter 指定 `sdk: docker`。

## 常用指令

### 本機開發

```powershell
# 建立虛擬環境（依專案規範一律用 uv，禁用 pip）
uv venv
uv pip install -r requirements.txt

# 設定環境變數（見下方「環境變數」章節）
$env:GEMINI_API_KEY = "..."
$env:LINE_CHANNEL_SECRET = "..."
$env:LINE_CHANNEL_ACCESS_TOKEN = "..."

# 用 Flask 開發伺服器直接跑某一支範例
uv run flask --app replybot run --port 7860
# 或用 gunicorn（與 Docker 部署一致）
uv run gunicorn -b 0.0.0.0:7860 replybot:app
```

`replybot` 可換成任一檔名（不含 `.py`）：`gemini`、`gpt4`、`multiturn`、`system_prompt`、`with_logs`、`with_search`、`example01`。

### Docker

```powershell
docker build -t sculinebot .
docker run --rm -p 7860:7860 `
  -e GEMINI_API_KEY=$env:GEMINI_API_KEY `
  -e LINE_CHANNEL_SECRET=$env:LINE_CHANNEL_SECRET `
  -e LINE_CHANNEL_ACCESS_TOKEN=$env:LINE_CHANNEL_ACCESS_TOKEN `
  sculinebot
```

`Dockerfile` 預設執行的入口是 `replybot:app`，若要 demo 其他範例，修改 `Dockerfile` 最後一行的 `CMD` 即可。`Dockerfile.old` 保留了舊版以 `gpt4:app` 為入口的設定，可作對照。

## 架構與規範

### 各檔案的定位

所有檔案都是**同一個 Flask + LINE Webhook 樣板**的不同變體，POST `/` 接 LINE webhook、GET `/` 做 health check。差別在於 LLM 的呼叫方式：

- `replybot.py` — **唯一的「正典」**。其他檔案的環境變數命名都應該以這支為準（見下方）。Gemini 單次呼叫、無 chat session。
- `multiturn.py` — 改用 `client.chats.create(...)` 維持多輪對話。
- `system_prompt.py` — 在單次呼叫中加 `system_instruction`。
- `with_logs.py` — 加上 `logging.basicConfig` 的版本。
- `with_search.py` — 把 `GoogleSearch` 當 tool 傳入 chat。
- `gemini.py` / `example01.py` — 完整版：除文字外，多了 `ImageMessageContent`、`VideoMessageContent` handler、`MessagingApiBlob` 下載媒體、Gemini 圖片生成 (`AI ` 前綴觸發)，並透過 `SPACE_HOST` 組出靜態圖片回傳 URL。`example01.py` 使用 `gemini-2.5-pro-preview` 並要求文言文輸出。
- `gpt4.py` — 把 LLM 換成 OpenAI `responses` API + DALL·E 3，並用 `previous_response_id` 串多輪。是「同樣的 LINE 樣板、不同 LLM」的對照組。

### 環境變數命名規範（重要）

`replybot.py` 是正典，所有檔案的環境變數必須與它一致：

| 用途 | 環境變數名 | Python 變數名 |
|---|---|---|
| Gemini API 金鑰 | `GEMINI_API_KEY` | `GEMINI_API_KEY` |
| LINE Channel Secret | `LINE_CHANNEL_SECRET` | `line_channel_secret` |
| LINE Channel Access Token | `LINE_CHANNEL_ACCESS_TOKEN` | `line_channel_access_token` |
| OpenAI 金鑰（僅 `gpt4.py`） | `OPENAI_API_KEY` | `OPENAI_API_KEY` |
| Hugging Face Space 主機名（僅媒體版本） | `SPACE_HOST` | `base_url` |

Hugging Face Spaces 的 Secrets 介面也應該用以上名稱設定。**新增範例檔時請延用同一組命名**，不要再引入 `GOOGLE_API_KEY` / `YOUR_CHANNEL_SECRET` / `YOUR_CHANNEL_ACCESS_TOKEN` 等舊名（這些已在 2026 年初統一掉了）。

### LINE SDK 版本

統一使用 **`linebot.v3`** 系列 API（`WebhookHandler`、`ApiClient`、`MessagingApi`、`MessagingApiBlob`、`ReplyMessageRequest`、`TextMessage`、`ImageMessage`、`MessageEvent`、`TextMessageContent`、`ImageMessageContent`、`VideoMessageContent`）。請勿混用舊版 `linebot`（v2）。

### Markdown → 純文字

Gemini／GPT 回應可能含 Markdown，但 LINE 不渲染 Markdown，因此所有範例的固定流程是：

```python
html = markdown.markdown(response_text)
text = BeautifulSoup(html, "html.parser").get_text()
```

新增 LLM 範例時請維持這個 pipeline。

### 圖片／影片處理約定（`gemini.py`、`example01.py`、`gpt4.py`）

- 透過 `MessagingApiBlob.get_message_content(message_id=...)` 下載原始 bytes。
- 暫存到 `tempfile.gettempdir()`，並用 `@app.route("/images/<filename>")` 提供回傳給 LINE 的公開 URL。
- 對外 URL 是 `https://{SPACE_HOST}/images/{filename}`——`SPACE_HOST` 是 Hugging Face Spaces 自動注入的環境變數，本機開發需要自己模擬或用 ngrok 等 tunneling 工具。
- `gpt4.py` 處理圖片時改用 base64 data URI 而非 URL（OpenAI vision input 的格式要求）。
- 文字訊息以 `AI ` 開頭代表「生成圖片」的命令，prompt 是去掉前綴的剩餘字串。

### Docker / 部署

`Dockerfile` 的 `CMD` 寫死了入口模組（預設 `replybot:app`）。若要切換要 demo 的範例：

1. 改 `Dockerfile` 最後一行的模組名。
2. Hugging Face Spaces 會自動 rebuild。

容器內部固定監聽 `0.0.0.0:7860`，這也是 HF Spaces 預期的 port。Healthcheck 打 `http://0.0.0.0:7860/`，所以新範例必須保留 GET `/` 的 health endpoint。

## 開發注意事項

- 修改任一範例時，**保持與 `replybot.py` 的變數命名一致**，這是這個 repo 的核心慣例。
- 加新範例時，沿用 `<檔名>:app` 可被 gunicorn 直接 serve 的結構（檔案頂層要有 `app = Flask(__name__)`）。
- `requirements.txt` 與 `test_requirements.txt` 內容幾乎相同，差別只在註解；新套件記得兩邊都加。
- 課程性質的 repo，**不要過度抽象**——把每個範例獨立、可單檔閱讀的特性保留下來，不要把共用程式抽成 module 而毀掉教學的可讀性。

## 環境設定

- 作業系統：Windows 11，Intel 12400，NVIDIA 4060（8GB VRAM），64GB RAM
- CUDA 13.0，driver 580
- 優先使用 CUDA，必要時才退回 CPU

## 工具鏈規範

- 服務一律用 Docker，避免 native 安裝
- 安裝工具優先用 winget
- **禁用 pip**，Python 一律用 `uv` venv，偏好 `uvx`
- Node.js 透過 nvm，套件用 npm/npx
- 每個專案推到公開 GitHub repo（repo 名稱 = 資料夾名稱）
- 測試要求：unit、functional、e2e（含瀏覽器工具），確保覆蓋率
- 絕不貼出機密/金鑰/token，從環境變數或 `.env` 讀取
- API/函式/程式碼先查網路（用 context7）
- 優先使用 CLI
- 開始工作前先執行 `pwd`
- 存取上層目錄前須取得確認

## 回答與行為偏好（重要）

- **回覆語言**：一律繁體中文（台灣），禁用簡體中文或中國大陸用語。
- **逗號**：回答時一律加上逗號，不管語氣再怎麼口語化都一樣。
- **稱呼**：不管任何情況，都不叫使用者的名字，一律用「你」。
- **不硬扯資料科學**：不要不管什麼話題都往資料科學方向聯結。
- **修改完自動更新 README.md**：每次修改完專案檔案後，要自動一併更新 `README.md`，不需要使用者另外提醒。
- **生成後附路徑**：每次生成完任何檔案，都要附上完整的檔案路徑告訴使用者。
- **未收到開始指令前不動檔案**：在使用者明確說要開始修改之前，只輸出文字，不執行任何指令或修改任何檔案。

## 簡報設計規範

製作、修改或審閱任何簡報時，請遵守以下規則：

### 事前確認
- 先寫出「核心訊息」：聽完這場報告，觀眾應該記住什麼（一句話）。
- 確認受眾、時間限制（目標張數 ≈ 分鐘數）。

### 結構
- 開場（1–2 張）→ 正文 → 結尾，每張只有一個重點。
- 標題要是完整句子，說出結論，不是主題標籤。
- 最後一張不能只有「謝謝」，要放結論與下一步。

### 文字
- 最多 5 個條列，每條約 15–20 中文字。
- 說明放 speaker notes，不貼演講稿到投影片上。
- 所有數字要有單位和比較基準，並標明來源。

### 版面與字型
- 最多 6 個元素，標題統一位置和大小。
- 中文字型用無襯線（微軟正黑體、Noto Sans TC）。
- 標題 ≥ 40pt，內文 ≥ 24pt，圖表標籤 ≥ 14pt。

### 顏色
- 2–3 色，強調色每張只用一次。
- 確保對比度，避免純紅/綠配色（色盲友善）。

### 圖表
- 不用 3D 圖，直接標註數值。
- 強調重點用強調色，其他用灰色。
- 依用途選擇正確圖表類型（比較→長條、趨勢→折線、佔比→圓餅、關係→散點）。
