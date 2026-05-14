"""Pipeline Step 1 — Nghia Ho OpenCV two-pass video stabilization with audio muxing."""

import asyncio
import shutil
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import get_logger
from app.models.video import Video, VideoStatus

logger = get_logger(__name__)

SMOOTHING_RADIUS = 15


async def stabilize_video(video_id: str, db: AsyncSession) -> str:
    """Run Nghia Ho OpenCV stabilization on raw video, mux audio, update DB."""
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise ValueError(f"Video {video_id} not found")
    if not video.raw_path:
        raise ValueError(f"Video {video_id} has no raw_path")

    video.status = VideoStatus.STABILIZING
    await db.commit()
    logger.info("status_stabilizing", video_id=video_id)

    raw_name = Path(video.raw_path).name
    raw_path = settings.MEDIA_RAW_DIR / raw_name
    if not raw_path.exists():
        raise FileNotFoundError(f"Raw video not found: {raw_path}")

    temp_path = settings.MEDIA_PROCESSED_DIR / f"{video_id}_noaudio.mp4"
    output_path = settings.MEDIA_PROCESSED_DIR / f"{video_id}_stabilized.mp4"
    settings.MEDIA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            _stabilize_sync,
            str(raw_path), str(temp_path),
        )

        logger.info("stabilization_write_done", video_id=video_id, temp=str(temp_path))

        await loop.run_in_executor(
            None,
            _mux_audio,
            str(raw_path), str(temp_path), str(output_path),
        )

        logger.info("stabilization_audio_muxed", video_id=video_id, output=str(output_path))

        if temp_path.exists():
            temp_path.unlink()

        video.status = VideoStatus.AUDIO_PROCESSING
        video.stabilized_at = datetime.now(timezone.utc)
        video.processed_path = str(output_path)
        await db.commit()

        logger.info("status_audio_processing", video_id=video_id)
        return str(output_path)

    except Exception:
        video.status = VideoStatus.FAILED
        video.failed_at = datetime.now(timezone.utc)
        await db.commit()
        raise


def _stabilize_sync(raw_path: str, temp_path: str) -> None:
    """Two-pass Nghia Ho stabilization. CPU-bound, runs in executor."""
    cap = cv2.VideoCapture(raw_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {raw_path}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total == 0:
        cap.release()
        raise RuntimeError("Video has zero frames")

    # Downsample for motion estimation only — 4x fewer pixels, same quality transforms
    SCALE = 0.5
    sw, sh = int(width * SCALE), int(height * SCALE)

    logger.info("stabilization_pass1_start", frames=total, dims=f"{width}x{height}", scale=SCALE)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(temp_path, fourcc, fps, (width, height))

    # ─── Pass 1: Motion estimation (at half resolution) ─────────────────
    trajectories = []  # list of [dx, dy, da]
    prev_gray = None

    for idx in range(total):
        ret, frame = cap.read()
        if not ret:
            break

        small = cv2.resize(frame, (sw, sh), interpolation=cv2.INTER_LINEAR)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

        if prev_gray is None:
            trajectories.append([0.0, 0.0, 0.0])
            prev_gray = gray
            continue

        features = cv2.goodFeaturesToTrack(
            prev_gray, maxCorners=100, qualityLevel=0.01,
            minDistance=15, blockSize=3,
        )

        dx, dy, da = 0.0, 0.0, 0.0

        if features is not None and len(features) >= 4:
            next_features, status, _ = cv2.calcOpticalFlowPyrLK(
                prev_gray, gray, features, None,
                winSize=(15, 15), maxLevel=2,
                criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03),
            )

            good_prev = features[status == 1]
            good_next = next_features[status == 1]

            if len(good_prev) >= 4:
                transform = cv2.estimateAffinePartial2D(good_prev, good_next)
                if transform is not None and transform[0] is not None:
                    mat = transform[0]
                    # Scale translation back to full resolution
                    dx = mat[0, 2] / SCALE
                    dy = mat[1, 2] / SCALE
                    da = np.arctan2(mat[1, 0], mat[0, 0])

        trajectories.append([dx, dy, da])
        prev_gray = gray

        if idx % 100 == 0 and idx > 0:
            logger.debug("stabilization_pass1_frame", frame=idx, total=total)

    cap.release()
    n_frames = len(trajectories)

    # ─── Smooth ─────────────────────────────────────────────────────────
    logger.info("stabilization_smoothing", frames=n_frames)
    traj_arr = np.array(trajectories, dtype=np.float64)
    smoothed = np.zeros_like(traj_arr)

    for i in range(n_frames):
        left = max(0, i - SMOOTHING_RADIUS)
        right = min(n_frames, i + SMOOTHING_RADIUS + 1)
        smoothed[i] = np.mean(traj_arr[left:right], axis=0)

    corrections = smoothed - traj_arr

    logger.info("stabilization_pass2_start", frames=n_frames)

    # ─── Pass 2: Frame warping ─────────────────────────────────────────
    # We wrote no frames to writer during pass 1.  Re-read from start.
    cap = cv2.VideoCapture(raw_path)

    for idx in range(n_frames):
        ret, frame = cap.read()
        if not ret:
            break

        dx = traj_arr[idx, 0] + corrections[idx, 0]
        dy = traj_arr[idx, 1] + corrections[idx, 1]
        da = traj_arr[idx, 2] + corrections[idx, 2]

        cos_a = np.cos(da)
        sin_a = np.sin(da)
        transform = np.array([
            [cos_a, -sin_a, dx],
            [sin_a,  cos_a, dy],
        ], dtype=np.float32)

        stabilized = cv2.warpAffine(
            frame, transform, (width, height),
            borderMode=cv2.BORDER_REFLECT,
        )
        writer.write(stabilized)

        if idx % 100 == 0 and idx > 0:
            logger.debug("stabilization_pass2_frame", frame=idx, total=n_frames)

    cap.release()
    writer.release()
    logger.info("stabilization_pass2_done", frames=n_frames)


def _mux_audio(raw_path: str, temp_path: str, output_path: str) -> None:
    """Copy audio from raw video into the stabilized video using PyAV."""
    import av

    raw = av.open(raw_path)
    raw_audio_streams = [s for s in raw.streams if s.type == "audio"]
    temp = av.open(temp_path)

    if not raw_audio_streams:
        raw.close()
        temp.close()
        shutil.copy2(temp_path, output_path)
        logger.info("stabilization_mux_no_audio", output=output_path)
        return

    output = av.open(output_path, mode="w")

    # Replicate video stream from temp (codec name + properties)
    in_video = temp.streams.video[0]
    out_video = output.add_stream(in_video.name, rate=in_video.average_rate)
    out_video.width = in_video.width
    out_video.height = in_video.height
    out_video.pix_fmt = in_video.pix_fmt
    if in_video.time_base:
        out_video.time_base = in_video.time_base

    # Replicate audio stream from raw
    in_audio = raw_audio_streams[0]
    out_audio = output.add_stream(in_audio.name, rate=in_audio.sample_rate)
    out_audio.layout = in_audio.layout
    out_audio.format = in_audio.format

    # Mux video packets from temp (video-only) output
    for packet in temp.demux(in_video):
        if packet.dts is not None:
            packet.stream = out_video
            output.mux(packet)

    # Mux audio packets from original raw file
    for packet in raw.demux(in_audio):
        if packet.dts is not None:
            packet.stream = out_audio
            output.mux(packet)

    output.close()
    raw.close()
    temp.close()
    logger.info("stabilization_mux_done", output=output_path)
