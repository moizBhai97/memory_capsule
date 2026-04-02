#!/usr/bin/env python3
"""Quick test of Whisper transcription config"""

import sys
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent))

from config import get_config
from providers import get_transcriber

def test_config():
    print("\n" + "="*60)
    print("MEMORY CAPSULE - WHISPER TRANSCRIPTION TEST")
    print("="*60 + "\n")

    # Load config
    config = get_config()

    print("📋 Transcriber Configuration:")
    print(f"   Model String    : {config.transcribe.model}")
    print(f"   Provider ID     : {config.transcribe.provider_id}")
    print(f"   Model ID        : {config.transcribe.model_id}")
    print(f"   Device          : {config.transcribe.device}")
    print(f"   Extra Config    : {config.transcribe.extra}\n")

    # Test transcriber initialization
    try:
        transcriber = get_transcriber(config)
        print(f"✓ Transcriber initialized successfully")
        print(f"   Type: {type(transcriber).__name__}\n")
    except Exception as e:
        print(f"✗ Failed to initialize transcriber: {e}\n")
        return False

    # Check if audio file exists
    audio_file = Path("data/test_inputs/voice_test.wav")
    if not audio_file.exists():
        print(f"✗ Audio file not found: {audio_file}\n")
        return False

    print(f"📁 Audio File: {audio_file}")
    print(f"   Size: {audio_file.stat().st_size} bytes\n")

    print("✓ All configuration checks passed!")
    print("✓ Ready to transcribe audio with Whisper\n")

    return True

if __name__ == "__main__":
    success = test_config()
    sys.exit(0 if success else 1)
