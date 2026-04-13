#!/usr/bin/env python3
"""
voice_pipeline.py — VieNeu-only Voice Pipeline
Pipeline: text → VieNeu-TTS → WAV → ffmpeg → selected audio format
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback

# Mặc định cho phép tải model nếu chưa có cache local.
# Có thể set HF_HUB_OFFLINE=1 từ môi trường để ép offline mode.
os.environ.setdefault("HF_HUB_OFFLINE", "0")
os.environ["ORT_LOGGING_LEVEL"] = "3" # Suppress ONNX Runtime warnings


def log_runtime_diag() -> None:
    try:
        print(f"[voice_pipeline] python={sys.version.split()[0]} platform={sys.platform}", file=sys.stderr)
        print(
            "[voice_pipeline] env "
            f"HF_HUB_OFFLINE={os.environ.get('HF_HUB_OFFLINE', '')} "
            f"USE_VIENEU_TTS={os.environ.get('USE_VIENEU_TTS', '')} "
            f"VIENEU_GPU_ENABLED={os.environ.get('VIENEU_GPU_ENABLED', '')}",
            file=sys.stderr,
        )
        cpu_flags = "unknown"
        if os.path.exists("/proc/cpuinfo"):
            with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.lower().startswith("flags"):
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            cpu_flags = " ".join(parts[1].strip().split()[:30])
                        break
        print(f"[voice_pipeline] cpu_flags={cpu_flags}", file=sys.stderr)
    except Exception as e:
        print(f"[voice_pipeline] diag error: {e}", file=sys.stderr)


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
        print(f"[voice_pipeline] {self.label} done", file=sys.stderr)

    def _run(self):
        i = 0
        while not self._stop.is_set():
            print(f"[voice_pipeline] {self.label} ... {i}s", file=sys.stderr)
            i += 1
            time.sleep(1.0)


def convert_audio(input_path: str, output_path: str, fmt: str) -> bool:
    try:
        f = (fmt or "aac").strip().lower().replace(".", "")
        codec_map = {
            "m4a": ["-c:a", "aac", "-b:a", "64k", "-profile:a", "aac_low", "-f", "mp4"],
            "aac": ["-c:a", "aac", "-b:a", "64k", "-f", "adts"],
            "mp3": ["-c:a", "libmp3lame", "-b:a", "96k", "-f", "mp3"],
            "ogg": ["-c:a", "libopus", "-b:a", "48k", "-f", "ogg"],
            "opus": ["-c:a", "libopus", "-b:a", "48k", "-f", "opus"],
            "wav": ["-c:a", "pcm_s16le", "-f", "wav"],
        }
        if f not in codec_map:
            f = "aac"
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-ar", "16000", "-ac", "1",
            "-map_metadata", "-1",
            "-movflags", "+faststart",
            *codec_map[f],
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            print(f"[voice_pipeline] ffmpeg error: {result.stderr[-300:]}", file=sys.stderr)
            return False
        if not os.path.exists(output_path) or os.path.getsize(output_path) < 500:
            return False
        return True
    except Exception as e:
        print(f"[voice_pipeline] ffmpeg failed: {e}", file=sys.stderr)
        return False


def vieneu_tts_to_wav(text: str, out_wav: str, ref_audio_override: str | None = None) -> bool:
    if os.environ.get("USE_VIENEU_TTS", "false").strip().lower() != "true":
        print("[voice_pipeline] USE_VIENEU_TTS=false", file=sys.stderr)
        return False

    try:
        from vieneu import Vieneu
        try:
            import vieneu
            print(f"[voice_pipeline] vieneu_version={getattr(vieneu, '__version__', 'unknown')}", file=sys.stderr)
        except Exception:
            pass
    except ImportError:
        print("[voice_pipeline] vieneu not installed", file=sys.stderr)
        return False

    t = (text or "").strip()
    t = re.sub(r'[*_~`#\[\]{}\\|<>^]', '', t)
    t = re.sub(r'[\U00010000-\U0010ffff]', '', t)
    t = re.sub(r'\s{2,}', ' ', t).strip()
    if not t:
        return False

    try:
        use_gpu = os.environ.get("VIENEU_GPU_ENABLED", "false").strip().lower() == "true"
        print(
            f"[voice_pipeline] GPU route env: NVIDIA_VISIBLE_DEVICES={os.environ.get('NVIDIA_VISIBLE_DEVICES', '')} "
            f"CUDA_VISIBLE_DEVICES={os.environ.get('CUDA_VISIBLE_DEVICES', '')} use_gpu={use_gpu}",
            file=sys.stderr,
        )
        if use_gpu:
            try:
                import torch
                if torch.cuda.is_available():
                    print(f"[voice_pipeline] CUDA device: {torch.cuda.get_device_name(0)}", file=sys.stderr)
            except Exception:
                pass
        try:
            with _ProgressTicker("loading VieNeu model (HF cache/download)"):
                tts = Vieneu(device="cuda" if use_gpu else "cpu")
        except TypeError:
            with _ProgressTicker("loading VieNeu model (legacy init)"):
                tts = Vieneu() # Fallback if Vieneu does not support device arg
        ref_audio = ref_audio_override or os.environ.get("VIENEU_REF_AUDIO", "").strip()
        voice_data = None
        if ref_audio:
            if ref_audio.startswith("vieneu:"):
                preset_key = ref_audio.split(":", 1)[1].strip().lower()
                try:
                    voices = tts.list_preset_voices()  # list of (desc, id)
                    # pick by id substring match
                    for desc, vid in voices:
                        if preset_key in str(vid).lower():
                            voice_data = tts.get_preset_voice(vid)
                            break
                    # fallback to first
                    if voice_data is None and voices:
                        voice_data = tts.get_preset_voice(voices[0][1])
                except Exception:
                    voice_data = None
            elif os.path.exists(ref_audio):
                voice_data = tts.encode_reference(ref_audio)

        audio = tts.infer(text=t, voice=voice_data) if voice_data is not None else tts.infer(text=t)
        tts.save(audio, out_wav)
        return os.path.exists(out_wav) and os.path.getsize(out_wav) > 500
    except Exception as e:
        print(f"[voice_pipeline] VieNeu error: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return False


def main():
    try:
        import faulthandler
        faulthandler.enable(file=sys.stderr, all_threads=True)
    except Exception:
        pass
    log_runtime_diag()

    parser = argparse.ArgumentParser()
    parser.add_argument("text", help="Text to synthesize")
    parser.add_argument("output", help="Output file path")
    parser.add_argument("--ref-audio", default=None, help="Override VIENEU_REF_AUDIO")
    parser.add_argument("--format", default=os.environ.get("VOICE_OUTPUT_EXT", "aac"), help="m4a|ogg|mp3|aac|wav|opus")
    args = parser.parse_args()

    text = (args.text or "").strip()
    if not text:
        print("[voice_pipeline] ERROR: empty text", file=sys.stderr)
        sys.exit(1)

    tmpdir = tempfile.mkdtemp(prefix="vieneu_")
    try:
        wav_path = os.path.join(tmpdir, "out.wav")
        ok = vieneu_tts_to_wav(text, wav_path, ref_audio_override=args.ref_audio)
        if not ok:
            print("[voice_pipeline] ERROR: VieNeu TTS failed", file=sys.stderr)
            sys.exit(1)

        out_ext = (args.format or "aac").strip().lower().replace(".", "")
        out_audio = os.path.join(tmpdir, f"out.{out_ext}")
        if convert_audio(wav_path, out_audio, out_ext):
            shutil.copy(out_audio, args.output)
        else:
            shutil.copy(wav_path, args.output)
        print(args.output)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()

