# Zalo AI Bot (Gemini + Whisper + VieNeu)

Bot chat nhóm Zalo, hỗ trợ hội thoại tự nhiên, phân tích ảnh/video/voice chat, và trả lời bằng giọng nói tiếng Việt. (Bot hiện tại khá mất dạy nếu muốn sửa lại tính cách của bot thì vào source code sửa lại. Tôi lười thêm environment vào cho Docker Image quá :3)

## Tính năng chính

- Chat ngắn gọn, tự nhiên, có cảm xúc theo ngữ cảnh.
- Phân tích ảnh/sticker bằng Gemini Vision.
- Phân tích video/meme bằng Gemini Video.
- Nhận diện giọng nói cục bộ bằng `faster-whisper`.
- Trả lời voice bằng VieNeu TTS.
- Ghi nhớ hành động gần đây để hạn chế trả lời mâu thuẫn trong hội thoại.
- Hỗ trợ tag/mention chính xác hơn với alias + UID.

## Cấu trúc project

- `bot.mjs`: luồng chính bot Zalo.
- `asr_local.py`: pipeline ASR local.
- `voice_pipeline.py`: synth voice + convert audio format.
- `Dockerfile.gpu`: image đầy đủ (GPU-friendly).
- `Dockerfile.cpu`: image CPU tối giản, nhẹ hơn.
- `docker-compose.image.cpu.example.yml`: file compose để build/chạy cấu hình CPU.
- `docker-compose.image.gpu.example.yml`: file compose để build/chạy cấu hình GPU.
- `docker-compose.gpu.example.yml`: biến thể GPU example dùng image có sẵn.
- `.env.cpu.example`, `.env.gpu.example`: file mẫu biến môi trường.

## Package và model đang dùng

### Node.js

- `zca-js`, `better-sqlite3`, `sharp`, `@jsquash/jxl`
- `pdf-parse`, `exceljs`, `mammoth`, `officeparser`
- `qrcode-terminal`

### Python

- `faster-whisper`, `yt-dlp`
- `vieneu` (hoặc `vieneu[gpu]` trên image GPU)
- `onnxruntime` (CPU) / `onnxruntime-gpu` (GPU)
- `numpy`, `pillow`, `soundfile`, `scipy`

### Model/provider

- LLM/Vision/Video: **Google Gemini API**
- ASR local: **Whisper** (`faster-whisper`)
- TTS: **VieNeu-TTS**

## Hướng dẫn Docker Compose (rõ ràng, theo từng trường hợp)

### 1) Chạy bằng các file compose build (khuyên dùng)

#### CPU

Image dùng sẵn: `ghcr.io/lam183/zalo-ai-cpu:latest`

```bash
cp .env.cpu.example .env
# sửa GEMINI_API_KEY, CLOUDFLARE_TUNNEL_TOKEN, VOICE_HOST_URL...
docker compose -f docker-compose.image.cpu.example.yml up -d --build
```

Nếu muốn chạy cả Cloudflare Tunnel cùng lúc:

```bash
docker compose -f docker-compose.image.cpu.example.yml --profile tunnel up -d --build
```

#### GPU

Yêu cầu host có NVIDIA driver + `nvidia-container-toolkit`.
Image dùng sẵn: `ghcr.io/lam183/zalo-ai-gpu:latest`

```bash
cp .env.gpu.example .env
# sửa GEMINI_API_KEY, CLOUDFLARE_TUNNEL_TOKEN, VOICE_HOST_URL...
docker compose -f docker-compose.image.gpu.example.yml up -d --build
```

Nếu muốn chạy cả Cloudflare Tunnel cùng lúc:

```bash
docker compose -f docker-compose.image.gpu.example.yml --profile tunnel up -d --build
```

## Hướng dẫn scan mã QR đăng nhập

Bot hỗ trợ 2 cách scan QR:

1. **Scan qua localhost (nhanh nhất)**  
   Khi bot khởi động và chưa có session, mở:
   - `http://localhost:3000`

2. **Scan qua file PNG**  
   QR được lưu thành file:
   - `./data/qr.png`
   Mở file này bằng app ảnh trên máy rồi dùng Zalo scan.

Lưu ý:
- `QR_PORT` mặc định là `3000`.
- `QR_FILE` mặc định là `./data/qr.png`.

### 2) Build image từ source rồi chạy

#### CPU nhẹ (dùng `Dockerfile.cpu`)

```bash
cp .env.cpu.example .env
docker build -f Dockerfile.cpu -t zalo-ai:cpu .
docker compose -f docker-compose.image.cpu.example.yml up -d --build
```

#### GPU (dùng `Dockerfile.gpu`)

```bash
cp .env.gpu.example .env
docker build -f Dockerfile.gpu -t zalo-ai:gpu .
docker compose -f docker-compose.image.gpu.example.yml up -d
```

## Vì sao cần Cloudflare Tunnel?

Bot cần gửi voice message qua URL public để client Zalo tải file audio ổn định.  
Container local trong mạng LAN/NAT thường không có domain public trực tiếp, nên Cloudflare Tunnel giúp:

- public endpoint an toàn cho `VOICE_HOST_URL` (không cần mở port router thủ công);
- giảm lỗi timeout/không tải được voice trên thiết bị khác mạng;
- đơn giản hóa triển khai khi chạy tại nhà/VPS sau NAT.

Bạn có thể **không dùng tunnel** nếu đã có domain public + reverse proxy riêng.  
Khi đó chỉ cần đặt `VOICE_HOST_URL` về URL public của bạn và không bật profile `tunnel`.

## Reference biến môi trường (đầy đủ)

Quy ước:
- **Bắt buộc**: cần set để bot chạy đúng.
- **Default CPU/GPU**: giá trị mặc định trong `.env.cpu.example` và `.env.gpu.example`.

### 1) Gemini API và model

- `GEMINI_API_KEY` — **Bắt buộc** — Default CPU/GPU: `your_gemini_api_key_1,your_gemini_api_key_2` — Danh sách API key Gemini (hỗ trợ nhiều key, ngăn cách dấu phẩy).
- `GEMINI_MODEL` — Tùy chọn — Default CPU/GPU: `gemini-3.1-flash-lite-preview,gemini-2.5-flash-lite,gemma-3-27b-it,gemini-3-flash-preview` — Danh sách model chat chính theo thứ tự fallback.
- `GEMINI_VISION_MODELS` — Tùy chọn — Default CPU/GPU: `gemini-2.5-flash,gemini-3-flash-preview,gemini-3-pro-preview,gemini-3.1-flash-lite-preview,gemini-2.5-flash-lite` — Model dùng cho phân tích ảnh.
- `GEMINI_SEARCH_MODELS` — Tùy chọn — Default CPU/GPU: `gemini-2.5-flash-lite,gemini-2.5-flash,gemini-3.1-flash-lite-preview,gemini-3-flash-preview,gemini-2.5-pro` — Model dùng khi có search/grounding.
- `GEMINI_AUDIO_MODEL` — Tùy chọn — Default CPU/GPU: `gemini-2.5-flash,gemini-2.5-flash-lite,gemini-3.1-flash-lite-preview,gemini-3-flash-preview,gemini-2.5-pro` — Model xử lý audio qua Gemini.

### 2) Cấu hình hành vi bot

- `SYSTEM_PROMPT` — Tùy chọn — Default CPU/GPU: `Yui - friendly Vietnamese chat bot. Keep replies short and natural.` — Persona và luật trả lời của bot.
- `GEMINI_TEMPERATURE` — Tùy chọn — Default CPU/GPU: `1.1` — Độ sáng tạo khi sinh nội dung.
- `ENABLE_SEARCH` — Tùy chọn — Default CPU/GPU: `false` — Bật/tắt search internet.
- `CAUTION_USERS` — Tùy chọn — Default CPU/GPU: (rỗng) — Danh sách user cần chú ý/ưu tiên xử lý theo logic riêng.
- `GROUP_PREFIX` — Tùy chọn — Default CPU/GPU: `"@yui "` — Prefix gọi bot trong nhóm.
- `BOT_MENTION_ALIASES` — Tùy chọn — Default CPU/GPU: `yui,commit,bot,ai` — Alias để bot nhận diện khi được gọi.
- `MEMBER_ALIASES` — Tùy chọn — Default CPU/GPU: (rỗng) — Mapping alias thành viên để tag chính xác hơn.
- `BOT_OWNER_NAME` — Tùy chọn — Default CPU/GPU: `Your Name` — Tên chủ bot.
- `BOT_OWNER_UID` — Tùy chọn — Default CPU/GPU: (rỗng) — UID chủ bot để xác thực chính xác chủ sở hữu.

### 3) Video + ASR local

- `VIDEO_AI_ENABLED` — Tùy chọn — Default CPU/GPU: `true` — Bật phân tích video.
- `VIDEO_AI_PROVIDER` — Tùy chọn — Default CPU/GPU: `gemini` — Provider phân tích video.
- `GEMINI_VIDEO_MODELS` — Tùy chọn — Default CPU/GPU: `gemini-2.5-flash-lite,gemini-3.1-flash-lite-preview,gemini-2.5-flash,gemini-3-flash-preview` — Danh sách model video fallback.
- `GEMINI_VIDEO_MODEL` — Tùy chọn — Default CPU/GPU: (rỗng) — Ép dùng 1 model video cố định.
- `GEMINI_VIDEO_TIMEOUT_MS` — Tùy chọn — Default CPU/GPU: `90000` — Timeout gọi Gemini video (ms).
- `GEMINI_VIDEO_POLL_MS` — Tùy chọn — Default CPU/GPU: `2500` — Chu kỳ poll trạng thái file video (ms).
- `GEMINI_VIDEO_POLL_TIMEOUT_MS` — Tùy chọn — Default CPU/GPU: `120000` — Timeout poll file video (ms).
- `YOUTUBE_VIDEO_AI_ENABLED` — Tùy chọn — Default CPU/GPU: `true` — Cho phép phân tích link YouTube.
- `VIDEO_ASR_MAX_SECONDS` — Tùy chọn — Default CPU/GPU: `120` — Thời lượng audio tối đa để ASR video.
- `VIDEO_FORCE_CPU` — Tùy chọn — Default CPU: `true` / GPU: `false` — Ép pipeline video/ASR chạy CPU.
- `VIDEO_LOCAL_FILES_ONLY` — Tùy chọn — Default CPU/GPU: `false` — Chỉ dùng file local, không download ngoài.
- `LOCAL_ASR_MODEL` — Tùy chọn — Default CPU/GPU: `large-v3-turbo` — Model Whisper local.
- `LOCAL_ASR_LANG` — Tùy chọn — Default CPU/GPU: `auto` — Ngôn ngữ ASR (`auto` để tự detect).
- `VIDEO_ASR_ALLOWED_LANGS` — Tùy chọn — Default CPU/GPU: `vi,en,ja` — Danh sách ngôn ngữ ASR chấp nhận.
- `LOCAL_ASR_FALLBACK_LANG` — Tùy chọn — Default CPU/GPU: `vi` — Ngôn ngữ fallback khi detect lệch.
- `LOCAL_ASR_BEAM_SIZE` — Tùy chọn — Default CPU/GPU: `5` — Beam size cho decode ASR.
- `LOCAL_ASR_OOM_FALLBACK_CPU` — Tùy chọn — Default CPU/GPU: `true` — Tự fallback CPU nếu ASR GPU bị OOM.
- `LOCAL_ASR_CPU_COMPUTE` — Tùy chọn — Default CPU/GPU: `int8` — Compute type cho ASR khi chạy CPU.
- `LOCAL_ASR_DEVICE` — Tùy chọn — Default CPU: `cpu` / GPU: `cuda` — Device ASR chính.
- `LOCAL_ASR_COMPUTE` — Tùy chọn — Default CPU: `int8` / GPU: `float16` — Compute type theo device ASR.

### 4) Voice/TTS

- `VOICE_ENABLED` — Tùy chọn — Default CPU/GPU: `false` — Bật gửi trả lời bằng voice (mặc định tắt cho dễ setup khi chưa có domain public).
- `VOICE_ONLY_MODE` — Tùy chọn — Default CPU/GPU: `false` — Ưu tiên chỉ gửi voice (không kèm text).
- `TRANSCRIPT` — Tùy chọn — Default CPU/GPU: `false` — Có gửi transcript text sau voice hay không.
- `TRANSCRIPT_DELAY_MS` — Tùy chọn — Default CPU/GPU: `1000` — Delay gửi transcript (ms).
- `VOICE_SEND_METHOD` — Tùy chọn — Default CPU/GPU: `voice_url_first` — Chiến lược gửi voice về Zalo.
- `VOICE_OUTPUT_EXT` — Tùy chọn — Default CPU/GPU: `m4a` — Định dạng file output (`m4a|ogg|mp3|aac|wav|opus`).
- `VOICE_NATIVE_EMULATION` — Tùy chọn — Default CPU/GPU: `true` — Bật chế độ giả lập voice native.
- `VOICE_NATIVE_TTL_MS` — Tùy chọn — Default CPU/GPU: `60000` — TTL cho chế độ native emulation (ms).
- `VIENEU_MAX_STRETCH_RATIO` — Tùy chọn — Default CPU/GPU: `2.6` — Ngưỡng co giãn thời lượng audio của VieNeu.
- `VOICE_PORT` — Tùy chọn — Default CPU/GPU: `3001` — Port HTTP serve voice file.
- `VOICE_HOST_URL` — **Khuyên dùng (gần như bắt buộc khi gửi voice qua URL)** — Default CPU/GPU: (rỗng) — URL public để client Zalo tải voice.
- `VOICE_NAME` — Tùy chọn — Default CPU/GPU: `vi-VN-HoaiMyNeural` — Tên voice fallback.
- `VOICE_PITCH` — Tùy chọn — Default CPU/GPU: `2` — Pitch voice fallback.
- `VOICE_TIMEOUT_S` — Tùy chọn — Default CPU/GPU: `300` — Timeout pipeline voice (giây).
- `VOICE_FILE_TTL_HOURS` — Tùy chọn — Default CPU/GPU: `720` — Thời gian giữ file voice đã tạo (giờ).

### 5) VieNeu TTS

- `USE_VIENEU_TTS` — Tùy chọn — Default CPU/GPU: `true` — Bật engine VieNeu.
- `VIENEU_GPU_ENABLED` — Tùy chọn — Default CPU: `false` / GPU: `true` — Bật tăng tốc GPU cho VieNeu.
- `VIENEU_MODE` — Tùy chọn — Default CPU/GPU: `turbo` — Chế độ chạy VieNeu.
- `VIENEU_MODELS` — Tùy chọn — Default CPU/GPU: `pnnbao-ump/VieNeu-TTS-v2-Turbo` — Danh sách model VieNeu fallback.
- `VIENEU_MODEL` — Tùy chọn — Default CPU/GPU: `pnnbao-ump/VieNeu-TTS-v2-Turbo` — Model VieNeu chính.
- `VIENEU_API_BASE` — Tùy chọn — Default CPU/GPU: (rỗng) — URL API khi dùng VieNeu remote mode.
- `VIENEU_REF_AUDIO` — Tùy chọn — Default CPU/GPU: (rỗng) — File audio reference cho voice clone.

### 6) Cloudflare Tunnel

- `CLOUDFLARE_TUNNEL_TOKEN` — **Bắt buộc nếu bật service tunnel** — Default CPU/GPU: `your_cloudflare_tunnel_token` — Token chạy cloudflared tunnel.

### 7) Google TTS (optional fallback)

- `GOOGLE_TTS_KEY_PATH` — Tùy chọn — Default CPU/GPU: `/app/data/gcloud-tts-key.json` — Đường dẫn service account JSON.
- `GOOGLE_TTS_VOICE` — Tùy chọn — Default CPU/GPU: `vi-VN-Neural2-A` — Voice Google TTS fallback.

### 8) Path và runtime chung

- `SESSION_FILE` — Tùy chọn — Default CPU/GPU: `./data/session.json` — Nơi lưu session đăng nhập Zalo.
- `HISTORY_DIR` — Tùy chọn — Default CPU/GPU: `./data/history` — Nơi lưu lịch sử hội thoại.
- `VOICE_TMP_DIR` — Tùy chọn — Default CPU/GPU: `/app/data/voice_tmp` — Thư mục file tạm voice.
- `TZ` — Tùy chọn — Default CPU/GPU: `Asia/Ho_Chi_Minh` — Timezone container.
- `ACTIVE_CONV_TTL_MS` — Tùy chọn — Default CPU/GPU: `120000` — Cửa sổ active conversation (ms).

### 9) NVIDIA routing (chỉ GPU)

- `NVIDIA_VISIBLE_DEVICES` — Tùy chọn (GPU) — Default GPU: `all` / CPU: không dùng — Expose toàn bộ GPU cho container.
- `CUDA_VISIBLE_DEVICES` — Tùy chọn (GPU) — Default GPU: `all` / CPU: không dùng — Cho CUDA dùng toàn bộ GPU.
- `ASR_CUDA_VISIBLE_DEVICES` — Tùy chọn (GPU) — Default GPU: để trống / CPU: không dùng — Để trống = không pin GPU riêng cho ASR.
- `VOICE_CUDA_VISIBLE_DEVICES` — Tùy chọn (GPU) — Default GPU: để trống / CPU: không dùng — Để trống = không pin GPU riêng cho TTS.
- `VIDEO_CUDA_VISIBLE_DEVICES` — Tùy chọn (GPU) — Default GPU: để trống / CPU: không dùng — Để trống = không pin GPU riêng cho video.

## Voice sample mặc định và cách thêm voice mới

Image hiện kèm sẵn:

- `/app/voice_samples/arisu.wav`
- `/app/voice_samples/hutao.wav`
- `/app/voice_samples/miku.wav`

### Dùng nhanh giọng clone cố định

Trong `.env`:

```env
VIENEU_REF_AUDIO=/app/voice_samples/hutao.wav
```

Sau đó rebuild/restart container.

### Thêm giọng mới

1. Đặt file vào `voice-samples/data/ref_audio/` (khuyên dùng `wav`/`flac`, 5-15 giây, ít noise).
2. Thêm dòng `COPY` tương ứng trong `Dockerfile.gpu` hoặc `Dockerfile.cpu`.
3. Build lại image.
4. Trỏ `VIENEU_REF_AUDIO` tới file mới trong container.

## Lệnh vận hành thường dùng

```bash
docker compose logs -f bot
docker compose restart bot
docker compose down
docker compose pull && docker compose up -d
```

## Troubleshooting nhanh

- Bot không trả lời: kiểm tra `GEMINI_API_KEY`, session Zalo, log container.
- Không gửi được voice: kiểm tra `VOICE_HOST_URL`, tunnel, cổng `3001`.
- GPU không hoạt động: kiểm tra `nvidia-smi` và toolkit Docker NVIDIA.
- ASR chậm: dùng GPU hoặc giảm model ASR trong `.env`.
