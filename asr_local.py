#!/usr/bin/env python3
import argparse
import json
import os
import sys
import threading
import time


def _is_cuda_oom(err: Exception) -> bool:
    s = str(err).lower()
    return "out of memory" in s or "cuda failed with error out of memory" in s or "cuda oom" in s


def _parse_allowed_langs(raw: str) -> set[str] | None:
    if not raw or not str(raw).strip():
        return None
    s = {x.strip().lower() for x in str(raw).split(",") if x.strip()}
    return s if s else None


def _segments_to_text(segments) -> str:
    text_parts = []
    for seg in segments:
        t = (seg.text or "").strip()
        if t:
            text_parts.append(t)
    return " ".join(text_parts).strip()


def _transcribe_once(model, audio_path: str, language, beam_size: int, vad: bool):
    segments, info = model.transcribe(
        audio_path,
        language=language,
        vad_filter=vad,
        beam_size=beam_size,
    )
    text = _segments_to_text(segments)
    return text, info


def _pick_fallback_lang(allowed: set[str], preferred: str) -> str:
    p = (preferred or "vi").strip().lower()
    if p in allowed:
        return p
    return sorted(allowed)[0]


class _ProgressTicker:
    def __init__(self, label: str):
        self.label = label
        self._stop = threading.Event()
        self._thread = None

    def __enter__(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        print(f"[asr_local] {self.label} done", file=sys.stderr)

    def _run(self):
        i = 0
        while not self._stop.is_set():
            print(f"[asr_local] {self.label} ... {i}s", file=sys.stderr)
            i += 1
            time.sleep(1.0)


def _transcribe_with_policy(model, audio_path: str, args, beam_size: int, vad: bool, allowed: set[str] | None):
    """
    allowed=None: giữ hành vi cũ (auto hoặc --lang cố định).
    allowed=set: chỉ chấp nhận ngôn ngữ trong tập; auto-detect rồi retry 1 lần nếu lệch.
    """
    lang = (args.lang or "").strip().lower()
    language_hint = None if (not lang or lang == "auto") else lang

    if language_hint is not None:
        if allowed is not None and language_hint not in allowed:
            fb = _pick_fallback_lang(allowed, os.environ.get("LOCAL_ASR_FALLBACK_LANG", "vi"))
            print(
                f"[asr_local] --lang={language_hint} not in allowed={allowed} -> using {fb}",
                file=sys.stderr,
            )
            language_hint = fb
        return _transcribe_once(model, audio_path, language_hint, beam_size, vad)

    # auto
    if allowed is None:
        return _transcribe_once(model, audio_path, None, beam_size, vad)

    fb = _pick_fallback_lang(allowed, os.environ.get("LOCAL_ASR_FALLBACK_LANG", "vi"))
    text, info = _transcribe_once(model, audio_path, None, beam_size, vad)
    detected = (getattr(info, "language", None) or "").strip().lower()
    if detected in allowed:
        return text, info
    print(
        f"[asr_local] detected={detected!r} not in allowed={allowed} -> re-transcribe with {fb}",
        file=sys.stderr,
    )
    text2, info2 = _transcribe_once(model, audio_path, fb, beam_size, vad)
    return text2, info2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", required=True, help="Path to audio file (wav/mp3/m4a/aac/ogg)")
    parser.add_argument("--lang", default=os.environ.get("LOCAL_ASR_LANG", "auto"), help="Language hint: auto|vi|en|...")
    parser.add_argument("--model", default=os.environ.get("LOCAL_ASR_MODEL", "medium"), help="faster-whisper model size")
    parser.add_argument("--device", default=os.environ.get("LOCAL_ASR_DEVICE", "cuda"), help="cuda|cpu|auto")
    parser.add_argument("--compute", default=os.environ.get("LOCAL_ASR_COMPUTE", ""), help="int8|int8_float16|float16|float32 (empty=auto)")
    parser.add_argument("--vad", action="store_true", help="Enable vad_filter")
    parser.add_argument("--beam-size", type=int, default=int(os.environ.get("LOCAL_ASR_BEAM_SIZE", "2")), help="Beam size for decoding")
    args = parser.parse_args()

    from faster_whisper import WhisperModel

    hf_home = os.environ.get("HF_HOME", None)
    xdg_home = os.environ.get("XDG_CACHE_HOME", None)
    if not xdg_home and hf_home:
        os.environ["XDG_CACHE_HOME"] = hf_home

    if os.environ.get("VIDEO_LOCAL_FILES_ONLY", "").strip().lower() == "true":
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    device = args.device
    if device == "auto":
        device = "cuda" if os.environ.get("CUDA_VISIBLE_DEVICES", "").strip() != "" else "cpu"
    print(
        f"[asr_local] route: NVIDIA_VISIBLE_DEVICES={os.environ.get('NVIDIA_VISIBLE_DEVICES', '')} "
        f"CUDA_VISIBLE_DEVICES={os.environ.get('CUDA_VISIBLE_DEVICES', '')} device={device}",
        file=sys.stderr,
    )

    allowed = _parse_allowed_langs(os.environ.get("LOCAL_ASR_ALLOWED_LANGS", "").strip())

    compute = (args.compute or "").strip().lower()
    if not compute:
        compute = "float16" if device.startswith("cuda") else "int8"

    compute_candidates = [compute]
    if device.startswith("cuda"):
        if compute == "int8_float16":
            compute_candidates = ["float16", "int8", "float32"]
        else:
            compute_candidates += ["float16", "int8", "float32"]
    else:
        compute_candidates += ["int8", "float32"]

    last_err = None
    download_root = hf_home
    model = None
    for c in compute_candidates:
        try:
            with _ProgressTicker(f"loading model={args.model} compute={c}"):
                model = WhisperModel(args.model, device=device, compute_type=c, download_root=download_root)
            last_err = None
            break
        except Exception as e:
            last_err = e
            model = None
    if model is None:
        raise RuntimeError(f"Failed to init WhisperModel (device={device}, compute tried={compute_candidates}): {last_err}")

    beam_size = max(1, min(5, int(args.beam_size or 2)))
    vad = bool(args.vad)

    def run_on_model(m):
        return _transcribe_with_policy(m, args.audio, args, beam_size, vad, allowed)

    try:
        text, info = run_on_model(model)
    except Exception as e:
        oom_fallback_cpu = os.environ.get("LOCAL_ASR_OOM_FALLBACK_CPU", "true").strip().lower() == "true"
        if not (device.startswith("cuda") and oom_fallback_cpu and _is_cuda_oom(e)):
            raise
        print("[asr_local] CUDA OOM -> retry on CPU", file=sys.stderr)
        cpu_compute = os.environ.get("LOCAL_ASR_CPU_COMPUTE", "int8").strip().lower() or "int8"
        with _ProgressTicker(f"loading cpu fallback model={args.model} compute={cpu_compute}"):
            model_cpu = WhisperModel(args.model, device="cpu", compute_type=cpu_compute, download_root=download_root)
        text, info = _transcribe_with_policy(
            model_cpu,
            args.audio,
            args,
            max(1, min(3, beam_size)),
            vad,
            allowed,
        )

    if not text:
        text = "[không nghe rõ]"

    out = {
        "text": text,
        "language": getattr(info, "language", None),
        "duration": getattr(info, "duration", None),
        "allowed_langs": sorted(allowed) if allowed else None,
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
