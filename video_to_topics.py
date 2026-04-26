#!/usr/bin/env python3
"""
Transcribes a video and generates a scannable topic outline with timestamps.
Usage: python video_to_topics.py <path-to-video>
"""

import sys
import os
import anthropic


def transcribe(video_path):
    import whisper
    print("Loading Whisper model (first run downloads ~140MB)...")
    model = whisper.load_model("base")
    print(f"Transcribing {os.path.basename(video_path)} — this may take a few minutes...")
    result = model.transcribe(video_path, verbose=False)
    return result["segments"]


def format_timestamp(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def format_transcript(segments):
    lines = []
    for seg in segments:
        ts = format_timestamp(seg["start"])
        lines.append(f"[{ts}] {seg['text'].strip()}")
    return "\n".join(lines)


def generate_topic_map(transcript_text, duration_minutes):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\nERROR: Set your ANTHROPIC_API_KEY environment variable first:")
        print("  export ANTHROPIC_API_KEY=your-key-here")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""This is a timestamped transcript of a {duration_minutes:.0f}-minute video.

<transcript>
{transcript_text}
</transcript>

Create a structured topic map to help me decide where to deep dive vs skim. Output:

1. **Executive Summary** (3-4 sentences covering the whole video)

2. **Topic Map** — list every major topic with:
   - Timestamp range (start → end)
   - Topic title
   - 1-sentence description
   - Recommendation: DEEP DIVE / SKIM / SKIP and why

3. **Quick Navigation** — a flat list of timestamps I can jump to:
   Format: [MM:SS] Topic name

Be specific with timestamps. If a topic repeats or connects to another, note it."""

    print("Sending transcript to Claude for analysis...")

    with client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=4096,
        thinking={"type": "adaptive"},
        cache_control={"type": "ephemeral"},
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        full_response = []
        for text in stream.text_stream:
            print(text, end="", flush=True)
            full_response.append(text)

    return "".join(full_response)


def save_output(video_path, topic_map):
    base = os.path.splitext(os.path.basename(video_path))[0]
    out_path = os.path.join(os.path.dirname(video_path) or ".", f"{base}_topics.md")
    with open(out_path, "w") as f:
        f.write(f"# Topic Map: {base}\n\n")
        f.write(topic_map)
    print(f"\n\nSaved to: {out_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python video_to_topics.py <path-to-video>")
        sys.exit(1)

    video_path = sys.argv[1]
    if not os.path.exists(video_path):
        print(f"File not found: {video_path}")
        sys.exit(1)

    segments = transcribe(video_path)
    if not segments:
        print("No speech detected in video.")
        sys.exit(1)

    total_seconds = segments[-1]["end"]
    duration_minutes = total_seconds / 60
    print(f"Transcribed {duration_minutes:.1f} minutes of content ({len(segments)} segments)")

    transcript_text = format_transcript(segments)

    # Save transcript too
    base = os.path.splitext(os.path.basename(video_path))[0]
    transcript_path = os.path.join(os.path.dirname(video_path) or ".", f"{base}_transcript.txt")
    with open(transcript_path, "w") as f:
        f.write(transcript_text)
    print(f"Transcript saved to: {transcript_path}\n")

    topic_map = generate_topic_map(transcript_text, duration_minutes)
    save_output(video_path, topic_map)


if __name__ == "__main__":
    main()
