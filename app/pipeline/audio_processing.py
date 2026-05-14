"""Pipeline Step 2 — noise removal and ASMR overlay using PyAV, noisereduce, and librosa."""

import asyncio
from pathlib import Path

import av
import librosa
import noisereduce
import numpy as np

from app.core.logging import get_logger

logger = get_logger(__name__)

BIRDS_PATH = Path("app/assets/birds.mp3")
WATER_PATH = Path("app/assets/water_stream.mp3")
BIRDS_VOLUME = 0.15
WATER_VOLUME = 0.10
NOISE_PROP_DECREASE = 0.75
CHUNK_SIZE = 1024


async def process_audio(video_path: str) -> str:
    """Extract audio from stabilized video, remove noise, overlay ASMR sounds, mux back into MP4."""
    input_path = Path(video_path)
    output_path = input_path.parent / input_path.name.replace("_stabilized.mp4", "_audio.mp4")

    logger.info("audio_extraction_start", input=str(input_path))

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _process_audio_sync, str(input_path), str(output_path))

    return str(output_path)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _frame_to_float32(frame: av.AudioFrame) -> np.ndarray:
    """Convert a PyAV AudioFrame to float32 ndarray (channels, samples) in [-1, 1]."""
    arr = frame.to_ndarray()
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    fmt = frame.format.name if frame.format else ""
    if "s16" in fmt:
        return arr.astype(np.float32) / 32768.0
    if "s32" in fmt:
        return arr.astype(np.float32) / 2147483648.0
    return arr.astype(np.float32)


def _load_asmr_file(path: Path, target_sr: int):
    """Load an MP3 asset with PyAV, resample if needed. Returns (channels, samples) float32."""
    if not path.exists():
        logger.warning("asmr_asset_missing", path=str(path))
        return None
    try:
        container = av.open(str(path))
        streams = [s for s in container.streams if s.type == "audio"]
        if not streams:
            container.close()
            return None
        stream = streams[0]
        src_sr = stream.sample_rate
        frames = [_frame_to_float32(f) for f in container.decode(stream)]
        container.close()
        if not frames:
            return None
        audio = np.concatenate(frames, axis=1)
        if src_sr != target_sr:
            audio = np.stack([
                librosa.resample(audio[ch], orig_sr=src_sr, target_sr=target_sr)
                for ch in range(audio.shape[0])
            ])
        return audio.astype(np.float32)
    except Exception as exc:
        logger.warning("asmr_asset_load_error", path=str(path), error=str(exc))
        return None


def _loop_to_length(arr: np.ndarray, target_len: int) -> np.ndarray:
    repeats = target_len // arr.shape[1] + 1
    return np.tile(arr, (1, repeats))[:, :target_len]


def _match_channels(arr: np.ndarray, n_channels: int) -> np.ndarray:
    src_ch = arr.shape[0]
    if src_ch == n_channels:
        return arr
    if src_ch == 1 and n_channels == 2:
        return np.tile(arr, (2, 1))
    if src_ch > 1 and n_channels == 1:
        return arr.mean(axis=0, keepdims=True)
    return np.tile(arr[:1], (n_channels, 1))


def _encode_video_h264(in_container, in_video_stream, out_video_stream, out_container) -> None:
    """Decode frames and re-encode as H.264. Both streams must be added before calling."""
    for frame in in_container.decode(in_video_stream):
        frame = frame.reformat(format="yuv420p")
        frame.pict_type = 0  # AV_PICTURE_TYPE_NONE
        for pkt in out_video_stream.encode(frame):
            out_container.mux(pkt)
    for pkt in out_video_stream.encode(None):
        out_container.mux(pkt)


def _encode_audio(out_container, out_audio_stream, audio: np.ndarray, sample_rate: int, n_channels: int) -> None:
    layout = "stereo" if n_channels == 2 else "mono"
    total_samples = audio.shape[1]
    pts = 0
    for start in range(0, total_samples, CHUNK_SIZE):
        chunk = audio[:, start : start + CHUNK_SIZE].astype(np.float32)
        frame = av.AudioFrame.from_ndarray(chunk, format="fltp", layout=layout)
        frame.sample_rate = sample_rate
        frame.pts = pts
        pts += chunk.shape[1]
        for packet in out_audio_stream.encode(frame):
            out_container.mux(packet)
    for packet in out_audio_stream.encode(None):
        out_container.mux(packet)


# ── Sync processing core ───────────────────────────────────────────────────────

def _process_audio_sync(input_path: str, output_path: str) -> None:
    """CPU-bound: extract audio → denoise → ASMR overlay → mux into output MP4."""

    # ── Step 1: Extract audio ──────────────────────────────────────────────
    in_container = av.open(input_path)
    audio_streams = [s for s in in_container.streams if s.type == "audio"]

    if not audio_streams:
        in_container.close()
        logger.info("audio_no_stream_mux_silent", input=input_path)
        _mux_silent(input_path, output_path)
        return

    in_audio_stream = audio_streams[0]
    sample_rate = in_audio_stream.sample_rate

    raw_frames = [_frame_to_float32(f) for f in in_container.decode(in_audio_stream)]
    in_container.close()

    audio: np.ndarray
    if raw_frames:
        audio = np.concatenate(raw_frames, axis=1)
    else:
        audio = np.zeros((1, sample_rate), dtype=np.float32)

    n_channels = audio.shape[0]
    total_samples = audio.shape[1]

    # ── Step 2: Noise removal ──────────────────────────────────────────────
    if total_samples >= sample_rate:
        logger.info("noise_reduction_start", channels=n_channels, samples=total_samples)
        if n_channels == 1:
            cleaned = noisereduce.reduce_noise(
                y=audio[0],
                sr=sample_rate,
                stationary=False,
                prop_decrease=NOISE_PROP_DECREASE,
            ).reshape(1, -1).astype(np.float32)
        else:
            cleaned = np.stack([
                noisereduce.reduce_noise(
                    y=audio[ch],
                    sr=sample_rate,
                    stationary=False,
                    prop_decrease=NOISE_PROP_DECREASE,
                ).astype(np.float32)
                for ch in range(n_channels)
            ])
        logger.info("noise_reduction_done")
    else:
        logger.info("noise_reduction_skipped_too_short", samples=total_samples)
        cleaned = audio

    # ── Step 3: ASMR overlay ───────────────────────────────────────────────
    logger.info("asmr_overlay_start")
    final = cleaned * 1.0

    for asset_path, volume, name in [
        (BIRDS_PATH, BIRDS_VOLUME, "birds"),
        (WATER_PATH, WATER_VOLUME, "water"),
    ]:
        asset = _load_asmr_file(asset_path, sample_rate)
        if asset is None:
            logger.warning("asmr_overlay_skipped", name=name)
            continue
        asset = _match_channels(asset, n_channels)
        looped = _loop_to_length(asset, total_samples)
        final = final + looped * volume

    final = np.clip(final, -1.0, 1.0).astype(np.float32)
    logger.info("asmr_overlay_done")

    # ── Step 4: Mux processed audio back ──────────────────────────────────
    logger.info("audio_mux_start")
    _mux_back(input_path, output_path, final, sample_rate, n_channels)
    logger.info("audio_mux_done", output=output_path)


def _mux_back(
    input_path: str,
    output_path: str,
    audio: np.ndarray,
    sample_rate: int,
    n_channels: int,
) -> None:
    """Re-encode video to H.264 + processed audio as AAC into browser-compatible MP4.
    All streams must be declared before muxing begins."""
    in_container = av.open(input_path)
    out_container = av.open(output_path, mode="w")

    video_streams = [s for s in in_container.streams if s.type == "video"]
    layout = "stereo" if n_channels == 2 else "mono"

    # Declare ALL streams first — required by FFmpeg before any mux call
    out_video = None
    if video_streams:
        in_v = video_streams[0]
        out_video = out_container.add_stream("libx264", rate=in_v.average_rate)
        out_video.width = in_v.width
        out_video.height = in_v.height
        out_video.pix_fmt = "yuv420p"
        out_video.options = {"preset": "fast", "crf": "23"}

    out_audio = out_container.add_stream("aac", rate=sample_rate, layout=layout)

    # Encode video then audio
    if out_video:
        _encode_video_h264(in_container, video_streams[0], out_video, out_container)

    _encode_audio(out_container, out_audio, audio, sample_rate, n_channels)

    out_container.close()
    in_container.close()


def _mux_silent(input_path: str, output_path: str) -> None:
    """Re-encode video to H.264 and inject a silent AAC track."""
    in_container = av.open(input_path)
    out_container = av.open(output_path, mode="w")

    video_streams = [s for s in in_container.streams if s.type == "video"]

    duration_secs = 0.0
    out_video = None
    if video_streams:
        in_v = video_streams[0]
        if in_v.duration and in_v.time_base:
            duration_secs = float(in_v.duration * in_v.time_base)
        out_video = out_container.add_stream("libx264", rate=in_v.average_rate)
        out_video.width = in_v.width
        out_video.height = in_v.height
        out_video.pix_fmt = "yuv420p"
        out_video.options = {"preset": "fast", "crf": "23"}

    sr = 44100
    n_samples = max(int(duration_secs * sr), CHUNK_SIZE)
    silent = np.zeros((1, n_samples), dtype=np.float32)

    out_audio = out_container.add_stream("aac", rate=sr, layout="mono")

    if out_video:
        _encode_video_h264(in_container, video_streams[0], out_video, out_container)

    _encode_audio(out_container, out_audio, silent, sr, 1)

    out_container.close()
    in_container.close()
