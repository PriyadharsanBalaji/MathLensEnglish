#!/usr/bin/env python3
"""
TTS Generation Script

Features:
- Read dialogue list from CSV file
- Generate audio using Edge TTS (xiaoxiao voice)
- Capture WordBoundary events to generate sentence-level sync points (sync_points)
- Output to specified directory
- Generate audio_info.json (including sync_points) for precise Manim animation alignment

CSV Format:
    filename,text
    audio_001_intro.wav,"Hello everyone, today we will learn..."
    audio_002_intro.wav,"First, let's look at this figure..."

Usage:
    python generate_tts.py audio_list.csv ./audio --voice xiaoxiao

Supported voices:
    xiaoxiao (female, default)
    xiaoyi (female)
    yunyang (male)
    yunjian (male)
"""

import sys
import os
import csv
import json
import re
import asyncio
from pathlib import Path

# Check edge-tts
try:
    import edge_tts
except ImportError:
    print("Error: edge-tts is not installed")
    print("Please run: uv pip install edge-tts")
    sys.exit(1)


# Voice mapping
VOICE_MAP = {
    'xiaoxiao': 'zh-CN-XiaoxiaoNeural',      # Xiaoxiao, female, default
    'xiaoyi': 'zh-CN-XiaoyiNeural',          # Xiaoyi, female
    'yunyang': 'zh-CN-YunyangNeural',        # Yunyang, male
    'yunjian': 'zh-CN-YunjianNeural',        # Yunjian, male
    'xiaoxiao-dialect': 'zh-CN-XiaoxiaoNeural',  # Xiaoxiao dialect
    'xiaoxiao-multilingual': 'zh-CN-XiaoxiaoMultilingualNeural',
}


async def generate_audio(text, output_path, voice='xiaoxiao'):
    """
    Generate single audio and capture WordBoundary sync data.

    Returns:
        (success, duration, sync_points)
        sync_points: List of sentence-level sync points [{idx, text, time}, ...]
    """
    voice_id = VOICE_MAP.get(voice, VOICE_MAP['xiaoxiao'])

    try:
        communicate = edge_tts.Communicate(text, voice_id)
        word_boundaries = []

        with open(output_path, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    word_boundaries.append({
                        "text": chunk["text"],
                        "offset": round(chunk["offset"] / 1e7, 3),
                        "duration": round(chunk["duration"] / 1e7, 3),
                    })

        duration = get_audio_duration(output_path)
        sync_points = build_sentence_sync_points(text, word_boundaries)
        return True, duration, sync_points
    except Exception as e:
        print(f"  Error generating {output_path}: {e}")
        return False, 0, []


def get_audio_duration(audio_path):
    """Get audio duration (seconds)"""
    try:
        from mutagen.mp3 import MP3
        audio = MP3(audio_path)
        return audio.info.length
    except Exception:
        pass

    try:
        from mutagen.wave import WAVE
        audio = WAVE(audio_path)
        return audio.info.length
    except Exception:
        pass

    try:
        import wave
        with wave.open(audio_path, 'rb') as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / float(rate)
    except Exception:
        pass

    return 0


def build_sentence_sync_points(original_text, word_boundaries):
    """
    Split sentences based on original text punctuation, and calculate
    start time using WordBoundary offset.

    Returns: [{idx, text, time}, ...]
    """
    if not word_boundaries:
        return []

    sentences = re.split(r'[。！？!?]+', original_text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return [{"idx": 0, "text": original_text[:40], "time": word_boundaries[0]["offset"]}]

    PUNCT = re.compile(r'[，,、；;：:（）()\s""\'\'""「」\-—…·。！？!?]')

    sync_points = []
    wb_idx = 0

    for sent_idx, sentence in enumerate(sentences):
        if wb_idx >= len(word_boundaries):
            break

        sync_points.append({
            "idx": sent_idx,
            "text": sentence[:40],
            "time": word_boundaries[wb_idx]["offset"],
        })

        clean = PUNCT.sub('', sentence)
        consumed = 0
        target = len(clean)

        while wb_idx < len(word_boundaries) and consumed < target:
            consumed += len(word_boundaries[wb_idx]["text"])
            wb_idx += 1

    return sync_points


def parse_csv(csv_path):
    """
    Parse CSV file

    Supported formats:
    - Standard CSV: filename,text
    - UTF-8 with BOM
    - Different delimiters (prioritize comma, supports semicolon)
    """
    entries = []

    # Try different encodings
    encodings = ['utf-8-sig', 'utf-8', 'gbk', 'gb2312']

    for encoding in encodings:
        try:
            with open(csv_path, 'r', encoding=encoding) as f:
                # Try detecting delimiter
                sample = f.read(2048)
                f.seek(0)

                delimiter = ','
                if ';' in sample and sample.count(';') > sample.count(','):
                    delimiter = ';'

                reader = csv.DictReader(f, delimiter=delimiter)

                for row in reader:
                    # Support different column names
                    filename = row.get('filename') or row.get('文件名') or row.get('file')
                    text = row.get('text') or row.get('对白') or row.get('content') or row.get('读白')

                    if filename and text:
                        entries.append({
                            'filename': filename,
                            'text': text.strip()
                        })

            print(f"✓ Parsed CSV successfully ({encoding}), {len(entries)} entries total")
            return entries

        except Exception as e:
            continue

    # If all fail, try simple parsing
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines[1:]:  # Skip header
                parts = line.strip().split(',', 1)
                if len(parts) == 2:
                    entries.append({
                        'filename': parts[0].strip(),
                        'text': parts[1].strip().strip('"')
                    })
        if entries:
            print(f"✓ Simple CSV parsing successful, {len(entries)} entries total")
            return entries
    except:
        pass

    print("Error: Could not parse CSV file")
    return []


async def generate_all(csv_path, output_dir, voice='xiaoxiao'):
    """Batch generate audio"""
    # Parse CSV
    entries = parse_csv(csv_path)
    if not entries:
        return False

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Generate audio
    results = []
    total = len(entries)

    print(f"\nGenerating audio (voice: {voice})...")
    print("="*50)

    for i, entry in enumerate(entries, 1):
        filename = entry['filename']
        text = entry['text']

        # Ensure correct extension
        if not filename.endswith(('.wav', '.mp3')):
            filename += '.wav'

        output_path = os.path.join(output_dir, filename)

        print(f"[{i}/{total}] {filename}")
        print(f"    Text: {text[:50]}{'...' if len(text) > 50 else ''}")

        success, duration, sync_points = await generate_audio(text, output_path, voice)

        if success:
            scene_num = extract_scene_number(filename)
            entry_result = {
                'scene': scene_num,
                'file': filename,
                'text': text,
                'duration': round(duration, 2),
                'sync_points': sync_points,
            }
            results.append(entry_result)
            print(f"    ✓ Duration: {duration:.2f}s | Sync points: {len(sync_points)} sentences")
        else:
            print(f"    ✗ Failed")

        print()

    # Generate audio_info.json
    if results:
        info = {
            'files': results,
            'total_duration': sum(r['duration'] for r in results),
            'count': len(results),
            'voice': voice
        }

        info_path = os.path.join(output_dir, 'audio_info.json')
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False, indent=2)

        print(f"Generated: {info_path}")

    return len(results) == len(entries)


def extract_scene_number(filename):
    """Extract scene number from filename"""
    # Support formats: audio_001_xxx.wav, scene_01_xxx.wav, 001_xxx.wav
    import re
    match = re.search(r'\d+', filename)
    if match:
        return int(match.group())
    return 0


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_tts.py <csv_file> [output_dir] [options]")
        print("")
        print("Arguments:")
        print("  csv_file      CSV file path")
        print("  output_dir    Output directory (default: ./audio)")
        print("")
        print("Options:")
        print("  --voice VOICE Voice selection (default: xiaoxiao)")
        print("")
        print("Available voices:")
        for k, v in VOICE_MAP.items():
            print(f"  {k:20s} - {v}")
        print("")
        print("Examples:")
        print("  python generate_tts.py audio_list.csv ./audio")
        print("  python generate_tts.py audio_list.csv ./audio --voice yunyang")
        sys.exit(1)

    csv_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else "./audio"

    # Parse options
    voice = 'xiaoxiao'
    for i, arg in enumerate(sys.argv):
        if arg == '--voice' and i + 1 < len(sys.argv):
            voice = sys.argv[i + 1]

    # Check file
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found: {csv_path}")
        sys.exit(1)

    print(f"CSV File: {csv_path}")
    print(f"Output Dir: {output_dir}")
    print(f"Using Voice: {voice}")
    print("")

    # Run
    success = asyncio.run(generate_all(csv_path, output_dir, voice))

    if success:
        print("\n✅ All generated successfully!")
        sys.exit(0)
    else:
        print("\n⚠️ Partial generation failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
