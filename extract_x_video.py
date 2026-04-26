import yt_dlp
import sys


def get_video_info(tweet_url):
    opts = {"quiet": True, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(tweet_url, download=False)


def download_video(tweet_url, output_path="%(uploader)s_%(id)s.%(ext)s", cookies_from_browser=None):
    opts = {
        "outtmpl": output_path,
        "format": "best",
    }
    if cookies_from_browser:
        opts["cookiesfrombrowser"] = (cookies_from_browser,)

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(tweet_url, download=True)
        print(f"Downloaded: {info.get('title') or info.get('id')}")
        return info


def get_direct_url(tweet_url):
    info = get_video_info(tweet_url)
    formats = info.get("formats", [])
    if formats:
        best = max(formats, key=lambda f: f.get("height") or 0)
        return best["url"]
    return info.get("url")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_x_video.py <tweet_url> [--url-only]")
        sys.exit(1)

    tweet_url = sys.argv[1]
    url_only = "--url-only" in sys.argv

    if url_only:
        direct_url = get_direct_url(tweet_url)
        print(direct_url)
    else:
        download_video(tweet_url)
