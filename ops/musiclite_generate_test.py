#!/opt/musiclite/venv/bin/python
"""Generate one deterministic MusicLite smoke-test track with ACE-Step."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from acestep.handler import AceStepHandler
from acestep.inference import GenerationConfig, GenerationParams, generate_music
from acestep.llm_inference import LLMHandler


def main() -> int:
    output_dir = Path(os.environ.get("MUSIC_AI_TEST_OUTPUT_DIR", "/var/lib/musiclite/output/test-1604"))
    output_dir.mkdir(parents=True, exist_ok=True)

    dit_handler = AceStepHandler()
    llm_handler = LLMHandler()
    status, ready = dit_handler.initialize_service(
        project_root="/opt/musiclite/generator",
        config_path="acestep-v15-turbo",
        device="cuda",
        use_flash_attention=False,
        compile_model=True,
        offload_to_cpu=True,
        offload_dit_to_cpu=True,
        quantization="int8_weight_only",
        use_mlx_dit=False,
    )
    if not ready:
        print(status, file=sys.stderr)
        return 2

    params = GenerationParams(
        task_type="text2music",
        caption=(
            "Original instrumental Brazilian electronic chill music, warm analog synths, "
            "gentle nylon-string guitar, subtle pandeiro and shaker, melodic electric bass, "
            "hopeful sunrise mood, spacious clean production, gradual intro, uplifting main "
            "theme and calm resolved outro; no vocals and no imitation of any artist or song"
        ),
        lyrics="[Instrumental]",
        instrumental=True,
        vocal_language="pt",
        bpm=104,
        keyscale="D Major",
        timesignature="4",
        duration=30.0,
        inference_steps=8,
        seed=1604,
        thinking=False,
        use_cot_metas=False,
        use_cot_caption=False,
        use_cot_lyrics=False,
        use_cot_language=False,
    )
    config = GenerationConfig(
        batch_size=1,
        use_random_seed=False,
        seeds=[1604],
        audio_format="wav",
    )
    result = generate_music(
        dit_handler,
        llm_handler,
        params,
        config,
        save_dir=str(output_dir),
    )
    if not result.success:
        print(result.error, file=sys.stderr)
        return 3

    summary = {
        "title": "Amanhecer 1604",
        "seed": 1604,
        "bpm": 104,
        "duration_requested": 30,
        "instrumental": True,
        "files": [audio.get("path") for audio in result.audios],
        "status": result.status_message,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
