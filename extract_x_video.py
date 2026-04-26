import yt_dlp
import sys


def _base_opts(cookies_from_browser=None, cookies_file=None):
    opts = {"quiet": True}
    if cookies_from_browser:
        opts["cookiesfrombrowser"] = (cookies_from_browser,)
    if cookies_file:
        opts["cookiefile"] = cookies_file
    return opts


def get_video_info(tweet_url, cookies_from_browser=None, cookies_file=None):
    opts = {**_base_opts(cookies_from_browser, cookies_file), "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(tweet_url, download=False)


def download_video(tweet_url, output_path="%(uploader)s_%(id)s.%(ext)s",
                   cookies_from_browser=None, cookies_file=None):
    opts = {
        **_base_opts(cookies_from_browser, cookies_file),
        "outtmpl": output_path,
        "format": "best",
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(tweet_url, download=True)
        print(f"Downloaded: {info.get('title') or info.get('id')}")
        return info


def get_direct_url(tweet_url, cookies_from_browser=None, cookies_file=None):
    info = get_video_info(tweet_url, cookies_from_browser, cookies_file)
    formats = info.get("formats", [])
    if formats:
        best = max(formats, key=lambda f: f.get("height") or 0)
        return best["url"]
    return info.get("url")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_x_video.py <tweet_url> [--url-only] [--browser chrome|firefox|safari] [--cookies path/to/cookies.txt]")
        print()
        print("X requires a logged-in session. Pass one of:")
        print("  --browser chrome     (reads cookies from your Chrome profile)")
        print("  --browser firefox    (reads cookies from your Firefox profile)")
        print("  --cookies cookies.txt  (a Netscape-format cookies file)")
        sys.exit(1)

    tweet_url = sys.argv[1]
    url_only = "--url-only" in sys.argv

    browser = None
    cookies_file = None
    if "--browser" in sys.argv:
        browser = sys.argv[sys.argv.index("--browser") + 1]
    if "--cookies" in sys.argv:
        cookies_file = sys.argv[sys.argv.index("--cookies") + 1]

    try:
        if url_only:
            direct_url = get_direct_url(tweet_url, browser, cookies_file)
            print(direct_url)
        else:
            download_video(tweet_url, cookies_from_browser=browser, cookies_file=cookies_file)
    except Exception as e:
        print(f"Error: {e}")
        if "403" in str(e) or "401" in str(e):
            print()
            print("X requires authentication. Try:")
            print("  python extract_x_video.py <url> --browser chrome")
            print("  python extract_x_video.py <url> --browser firefox")
        sys.exit(1)
