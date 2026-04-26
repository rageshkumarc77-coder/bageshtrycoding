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


def markdown_to_html(md):
    import re
    html = md
    # Headers
    html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)
    # Bold
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    # Inline code
    html = re.sub(r"`(.+?)`", r"<code>\1</code>", html)
    # Colour-code recommendation badges
    for label, cls in [("DEEP DIVE", "deep-dive"), ("SKIM", "skim"), ("SKIP", "skip")]:
        html = html.replace(label, f'<span class="badge {cls}">{label}</span>')
    # Horizontal rules
    html = re.sub(r"^---+$", "<hr>", html, flags=re.MULTILINE)
    # Bullet lists
    lines = html.split("\n")
    out, in_list = [], False
    for line in lines:
        if re.match(r"^\s*[-*] ", line):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append("<li>" + re.sub(r"^\s*[-*] ", "", line) + "</li>")
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(line)
    if in_list:
        out.append("</ul>")
    html = "\n".join(out)
    # Paragraphs — wrap non-tag lines
    paragraphs = []
    for block in re.split(r"\n{2,}", html):
        block = block.strip()
        if not block:
            continue
        if block.startswith("<"):
            paragraphs.append(block)
        else:
            paragraphs.append(f"<p>{block}</p>")
    return "\n".join(paragraphs)


def save_output(video_path, topic_map, duration_minutes):
    import datetime
    base = os.path.splitext(os.path.basename(video_path))[0]
    out_dir = os.path.dirname(video_path) or "."

    # Markdown
    md_path = os.path.join(out_dir, f"{base}_topics.md")
    with open(md_path, "w") as f:
        f.write(f"# Topic Map: {base}\n\n{topic_map}")

    # HTML
    body = markdown_to_html(topic_map)
    generated = datetime.datetime.now().strftime("%B %d, %Y %H:%M")
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Topic Map — {base}</title>
<style>
  :root {{
    --deep: #1a6b3c; --deep-bg: #d4edda;
    --skim: #856404; --skim-bg: #fff3cd;
    --skip: #721c24; --skip-bg: #f8d7da;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          background: #f5f5f5; color: #222; line-height: 1.7; }}
  .header {{ background: #1a1a2e; color: #fff; padding: 2rem 2.5rem; }}
  .header h1 {{ font-size: 1.6rem; font-weight: 700; margin-bottom: .25rem; }}
  .header .meta {{ font-size: .9rem; opacity: .7; }}
  .container {{ max-width: 860px; margin: 2rem auto; padding: 0 1.5rem 4rem; }}
  h2 {{ font-size: 1.25rem; font-weight: 700; margin: 2rem 0 .75rem;
        padding-bottom: .4rem; border-bottom: 2px solid #e0e0e0; color: #1a1a2e; }}
  h3 {{ font-size: 1.05rem; font-weight: 600; margin: 1.25rem 0 .4rem; color: #333; }}
  p {{ margin-bottom: .9rem; }}
  ul {{ margin: .5rem 0 .9rem 1.5rem; }}
  li {{ margin-bottom: .35rem; }}
  strong {{ font-weight: 600; }}
  code {{ background: #eee; padding: .1em .35em; border-radius: 3px;
          font-family: monospace; font-size: .9em; }}
  hr {{ border: none; border-top: 1px solid #ddd; margin: 1.5rem 0; }}
  .badge {{ display: inline-block; font-size: .75rem; font-weight: 700;
            padding: .2em .6em; border-radius: 4px; letter-spacing: .04em; }}
  .deep-dive {{ color: var(--deep); background: var(--deep-bg); }}
  .skim      {{ color: var(--skim); background: var(--skim-bg); }}
  .skip      {{ color: var(--skip); background: var(--skip-bg); }}
  .footer {{ margin-top: 3rem; font-size: .8rem; color: #999; text-align: center; }}
</style>
</head>
<body>
<div class="header">
  <h1>📋 Topic Map — {base}</h1>
  <div class="meta">{duration_minutes:.0f}-minute video &nbsp;·&nbsp; Generated {generated}</div>
</div>
<div class="container">
{body}
<div class="footer">Generated with Whisper + Claude Opus 4.7</div>
</div>
</body>
</html>"""

    html_path = os.path.join(out_dir, f"{base}_topics.html")
    with open(html_path, "w") as f:
        f.write(html)

    print(f"\n\nSaved:\n  {md_path}\n  {html_path}")
    print(f"\nOpen in browser:\n  open \"{html_path}\"")


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
    save_output(video_path, topic_map, duration_minutes)


if __name__ == "__main__":
    main()
