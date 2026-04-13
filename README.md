# Zalo AI Bot (Gemini + Whisper + VieNeu)

Bot chat nhóm Zalo dùng Google Gemini để hiểu ngữ cảnh hội thoại, ảnh, video; dùng Whisper để nhận diện giọng nói; và VieNeu TTS để trả lời bằng giọng Việt.

## 1) Bot này làm gì?

- Chat tự nhiên trong nhóm Zalo, ưu tiên câu trả lời ngắn gọn, có cảm xúc.
- Hiểu nội dung media:
  - Ảnh/sticker qua Gemini Vision.
  - Video/meme qua Gemini Video.
  - Voice chat/audio qua ASR cục bộ (`faster-whisper`).
- Có cơ chế nhớ hành động gần đây của bot trong thread để hạn chế trả lời sai kiểu "tôi chưa tag ai".
- Hỗ trợ nhắc tên/tag thành viên theo UID chính xác hơn bằng dữ liệu nhóm và alias.
- Hỗ trợ trả lời bằng giọng nói (VieNeu TTS), có thể chọn đuôi file audio xuất ra bằng `VOICE_OUTPUT_EXT` (ví dụ: `m4a`, `ogg`, `mp3`, `aac`, `wav`, `opus`).

## 2) Kiến trúc tổng quan

- `bot.mjs`: luồng chính của bot Zalo (nhận tin, gọi model, xử lý tag/mention, điều phối media, gửi phản hồi).
- `asr_local.py`: nhận diện giọng nói cục bộ bằng Whisper.
- `voice_pipeline.py`: pipeline tổng hợp giọng (VieNeu) và convert format audio bằng `ffmpeg`.
- `docker-compose.yml`: cấu hình chạy mặc định (build từ source).
- `docker-compose.gpu.yml`: override khi chạy chế độ GPU.
- `docker-compose.image.cpu.example.yml`: ví dụ chạy bằng image có sẵn (CPU).
- `docker-compose.image.gpu.example.yml`: ví dụ chạy bằng image có sẵn (GPU).
- `.env.cpu.example` và `.env.gpu.example`: mẫu biến môi trường tương ứng CPU/GPU.

## 3) Công nghệ, package và model đang dùng

### Node.js dependencies chính

- `zca-js`: kết nối và thao tác với Zalo.
- `better-sqlite3`: SQLite cho dữ liệu hội thoại/RAG.
- `sharp`, `@jsquash/jxl`: xử lý ảnh.
- `pdf-parse`, `xlsx`, `mammoth`, `officeparser`: đọc tài liệu.
- `qrcode-terminal`: hiển thị QR đăng nhập phiên Zalo.

### Python dependencies chính

- `torch`, `torchaudio`: nền tảng ML/ASR/TTS.
- `faster-whisper`: ASR cục bộ cho voice/audio/video.
- `yt-dlp`: lấy audio/video từ nguồn URL (ví dụ YouTube).
- `vieneu[gpu]`, `onnxruntime-gpu`: TTS tiếng Việt.
- `numpy`, `pillow`, `soundfile`, `scipy`: xử lý dữ liệu media.
- `ffmpeg`, `sox` (system packages): convert/audio processing.

### Model/provider

- LLM/vision/video/audio hiểu ngữ cảnh: **Google Gemini** (qua API).
- ASR local: **Whisper** (`faster-whisper`).
- TTS: **VieNeu-TTS** (`pnnbao-ump/VieNeu-TTS-v2-Turbo` mặc định).

Lưu ý: các thành phần Qwen/Piper/RVC trước đây đã được loại bỏ khỏi cấu hình hiện tại.

## 4) Cấu hình nhanh theo CPU hoặc GPU

### A. Chạy bằng image có sẵn (đơn giản cho người dùng)

#### CPU

1. Copy file môi trường:
   - `cp .env.cpu.example .env`
2. Điền các biến bắt buộc trong `.env`:
   - `GEMINI_API_KEY`
   - `CLOUDFLARE_TUNNEL_TOKEN`
   - (khuyên cấu hình thêm) `VOICE_HOST_URL`, `BOT_OWNER_NAME`, `BOT_OWNER_UID`
3. Chạy:
   - `docker compose -f docker-compose.image.cpu.example.yml up -d`

#### GPU

1. Máy phải có NVIDIA driver + `nvidia-container-toolkit`.
2. Copy file môi trường:
   - `cp .env.gpu.example .env`
3. Điền các biến bắt buộc:
   - `GEMINI_API_KEY`
   - `CLOUDFLARE_TUNNEL_TOKEN`
4. Chạy:
   - `docker compose -f docker-compose.image.gpu.example.yml up -d`

### B. Chạy build từ source trong repo

- CPU mặc định:
  - `cp .env.cpu.example .env`
  - `docker compose up -d --build`
- GPU:
  - `cp .env.gpu.example .env`
  - `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build`

## 5) Nhóm biến môi trường quan trọng

#### Bắt buộc

- `GEMINI_API_KEY`: API key Gemini (có thể nhiều key, ngăn cách dấu phẩy).
- `CLOUDFLARE_TUNNEL_TOKEN`: token tunnel để publish voice endpoint.

#### Model/AI

- `GEMINI_MODEL`: danh sách model chat chính.
- `GEMINI_VISION_MODELS`: model xử lý ảnh.
- `GEMINI_VIDEO_MODELS`, `GEMINI_VIDEO_MODEL`: model xử lý video.
- `GEMINI_AUDIO_MODEL`: model audio understanding của Gemini (nếu dùng).

#### Video + ASR

- `VIDEO_AI_ENABLED`: bật/tắt hiểu video.
- `VIDEO_AI_PROVIDER`: hiện tại dùng `gemini`.
- `YOUTUBE_VIDEO_AI_ENABLED`: bật phân tích video YouTube.
- `LOCAL_ASR_MODEL`: model Whisper (`large-v3-turbo` mặc định).
- `LOCAL_ASR_DEVICE`: `cpu` hoặc `cuda`.
- `LOCAL_ASR_COMPUTE`: `int8`, `float16`, ...
- `VIDEO_FORCE_CPU`: ép xử lý video/audio qua CPU.

#### Voice/TTS

- `VOICE_ENABLED`: bật trả lời bằng giọng.
- `VOICE_ONLY_MODE`: ưu tiên chế độ voice.
- `VOICE_SEND_METHOD`: cách gửi voice về Zalo.
- `VOICE_OUTPUT_EXT`: đuôi file audio đầu ra (`m4a`, `ogg`, `mp3`, `aac`, `wav`, `opus`).
- `USE_VIENEU_TTS`: bật VieNeu TTS.
- `VIENEU_GPU_ENABLED`: bật tăng tốc GPU cho TTS.
- `VOICE_HOST_URL`: domain public để client truy cập file voice.

#### Bot hành vi/tag

- `SYSTEM_PROMPT`: tính cách và rule trả lời.
- `GROUP_PREFIX`: tiền tố bot lắng nghe trong nhóm.
- `BOT_MENTION_ALIASES`: alias gọi bot.
- `MEMBER_ALIASES`: map alias thủ công cho thành viên để tag chính xác hơn.

#### Runtime/path

- `SESSION_FILE`: phiên đăng nhập Zalo.
- `HISTORY_DIR`: thư mục lịch sử/chat state.
- `VOICE_TMP_DIR`: thư mục file tạm TTS.
- `TZ`: timezone container.

#### GPU runtime

- `NVIDIA_VISIBLE_DEVICES`, `CUDA_VISIBLE_DEVICES`: chọn GPU.
- `ASR_CUDA_VISIBLE_DEVICES`, `VOICE_CUDA_VISIBLE_DEVICES`, `VIDEO_CUDA_VISIBLE_DEVICES`: tách GPU theo tác vụ.

## 6) Bảo mật khi push GitHub

Repo đã có `.gitignore` để tránh đẩy dữ liệu nhạy cảm như:

- file `.env` thật;
- session/token/key/cert cục bộ;
- cache model (`hf_cache`, `torch_cache`, `models`);
- log/file tạm.

Khuyến nghị thêm:

- Không commit file secret trong `data/`.
- Nếu lỡ commit secret, rotate key ngay (Gemini, Cloudflare, ...).

## 7) Lệnh vận hành thường dùng

- Xem log:
  - `docker compose logs -f bot`
- Restart bot:
  - `docker compose restart bot`
- Tắt toàn bộ:
  - `docker compose down`
- Cập nhật image và chạy lại:
  - `docker compose pull && docker compose up -d`

## 8) Troubleshooting nhanh

- Bot không trả lời:
  - kiểm tra `GEMINI_API_KEY`, log container, và session Zalo còn hiệu lực.
- Không gửi được voice:
  - kiểm tra `VOICE_HOST_URL`, tunnel, và port `3001`.
- GPU không hoạt động:
  - kiểm tra `nvidia-smi` trên host, toolkit Docker NVIDIA, và file compose GPU.
- ASR chậm:
  - dùng `.env.gpu.example` + `LOCAL_ASR_DEVICE=cuda` nếu có GPU.

## 9) Voice samples mặc định và cách thêm giọng mới

Image build hiện đã kèm sẵn 3 sample voice clone:

- `/app/voice_samples/arisu.wav`
- `/app/voice_samples/hutao.wav`
- `/app/voice_samples/miku.wav`

### Dùng nhanh 1 giọng clone cố định cho bot

1. Mở `.env`.
2. Set `VIENEU_REF_AUDIO` về 1 file sample, ví dụ:
   - `VIENEU_REF_AUDIO=/app/voice_samples/hutao.wav`
3. Rebuild/restart container:
   - `docker compose up -d --build`

### Cách thêm voice mới của bạn

1. Chuẩn bị audio mẫu chất lượng sạch (khuyến nghị 5-15 giây, ít tạp âm).
2. Đặt file vào thư mục:
   - `voice-samples/data/ref_audio/`
3. Cập nhật `Dockerfile` để copy file đó vào image (theo cùng pattern đang copy `arisu/hutao/miku`).
4. Build lại image:
   - `docker compose build --no-cache`
   - hoặc `docker compose up -d --build`
5. Trỏ `VIENEU_REF_AUDIO` sang file mới trong container (ví dụ `/app/voice_samples/ten-voice.wav`) rồi restart bot.

Gợi ý format: ưu tiên `wav` hoặc `flac`; nếu dùng `mp3/m4a` vẫn hoạt động nhưng chất lượng clone có thể kém hơn file lossless.
