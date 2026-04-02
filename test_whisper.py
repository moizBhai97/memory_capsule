#!/usr/bin/env python3
"""Test Whisper transcription via CLI"""

import asyncio
import sys
from pathlib import Path

async def test_whisper():
    # Setup path
    sys.path.insert(0, str(Path(__file__).parent))

    from cli import _cmd_add
    from config import get_config
    from capsule.models import SourceApp
    import argparse

    # Check config
    config = get_config()
    print(f"\n=== Whisper Configuration ===")
    print(f"Transcriber: {config.transcribe.model}")
    print(f"Provider: {config.transcribe.provider_id}")
    print(f"Model ID: {config.transcribe.model_id}")
    print(f"Device: {config.transcribe.device}\n")

    # Simulate CLI args
    class Args:
        file = "data/test_inputs/voice_test.wav"
        text = None
        url = None
        sender = None
        source = "whisper-test"

    args = Args()

    print(f"Processing audio file: {args.file}\n")
    try:
        await _cmd_add(args)
        print("\n✓ Whisper test completed successfully!")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_whisper())
