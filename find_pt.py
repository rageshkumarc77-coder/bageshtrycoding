#!/usr/bin/env python3
"""
Find top-rated Physical Therapists in the Bay Area accepting Anthem insurance.
Pulls from Yelp (ratings) and Healthgrades (insurance verification).
Usage: python find_pt.py
Requires: YELP_API_KEY env var  (free at https://fusion.yelp.com)
"""

import os
import sys
import time
import re
import json
import requests
from datetime import datetime
from bs4 import BeautifulSoup

YELP_API_KEY = os.environ.get("YELP_API_KEY", "")

BAY_AREA_CITIES = [
    "San Francisco, CA",
    "Oakland, CA",
    "San Jose, CA",
    "Berkeley, CA",
    "Palo Alto, CA",
    "Fremont, CA",
    "Walnut Creek, CA",
    "San Mateo, CA",
    "Santa Clara, CA",
    "Marin County, CA",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# ── Yelp ──────────────────────────────────────────────────────────────────────

def yelp_search(city, api_key):
    url = "https://api.yelp.com/v3/businesses/search"
    params = {
        "term": "physical therapist",
        "location": city,
        "categories": "physicaltherapy",
        "limit": 20,
        "sort_by": "rating",
    }
    resp = requests.get(url, headers={"Authorization": f"Bearer {api_key}"}, params=params, timeout=10)
    if resp.status_code == 401:
        print("ERROR: Invalid Yelp API key. Get a free one at https://fusion.yelp.com")
        sys.exit(1)
    if resp.status_code != 200:
        return []
    return resp.json().get("businesses", [])


def collect_yelp(api_key):
    print("Searching Yelp across Bay Area cities...")
    seen, results = set(), []
    for city in BAY_AREA_CITIES:
        businesses = yelp_search(city, api_key)
        for b in businesses:
            if b["id"] in seen:
                continue
            seen.add(b["id"])
            loc = b.get("location", {})
            results.append({
                "name": b["name"],
                "rating": b.get("rating", 0),
                "review_count": b.get("review_count", 0),
                "address": ", ".join(loc.get("display_address", [])),
                "city": loc.get("city", city.split(",")[0]),
                "phone": b.get("display_phone", "—"),
                "yelp_url": b.get("url", ""),
                "anthem": None,  # filled in by Healthgrades check
            })
        print(f"  {city}: {len(businesses)} found")
        time.sleep(0.25)
    print(f"  Total unique: {len(results)}\n")
    return results


# ── Healthgrades ──────────────────────────────────────────────────────────────

def healthgrades_anthem_names():
    """Return a set of provider names that appear on Healthgrades with Anthem."""
    print("Checking Healthgrades for Anthem-accepting providers...")
    names = set()
    search_terms = ["physical therapist bay area", "physical therapy san francisco"]
    base = "https://www.healthgrades.com/usearch"
    for term in search_terms:
        try:
            params = {
                "what": "Physical Therapist",
                "where": "San Francisco Bay Area, CA",
                "insuranceCarrier": "Anthem Blue Cross",
            }
            resp = requests.get(base, params=params, headers=HEADERS, timeout=12)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            # Healthgrades provider names sit in various selectors depending on page version
            for tag in soup.select("[data-qa-target='provider-name'], .provider-name, h2.name"):
                name = tag.get_text(strip=True)
                if name:
                    names.add(name.lower())
            time.sleep(1)
        except Exception:
            pass
    print(f"  Healthgrades names found: {len(names)}\n")
    return names


def flag_anthem(results, anthem_names):
    """Mark providers whose names fuzzy-match the Healthgrades Anthem list."""
    for r in results:
        norm = r["name"].lower()
        # Exact or partial name match
        r["anthem"] = any(
            norm in a or a in norm or
            norm.split()[0] in a  # match on first word (clinic name prefix)
            for a in anthem_names
        ) if anthem_names else None
    return results


# ── HTML output ───────────────────────────────────────────────────────────────

def stars(rating):
    full = int(rating)
    half = 1 if (rating - full) >= 0.5 else 0
    empty = 5 - full - half
    return "★" * full + ("½" if half else "") + "☆" * empty


def anthem_badge(val):
    if val is True:
        return '<span class="badge confirmed">✓ Anthem listed</span>'
    if val is False:
        return '<span class="badge not-listed">Not on Healthgrades</span>'
    return '<span class="badge unknown">⚠ Verify by phone</span>'


def build_html(results, generated):
    rows = ""
    for i, r in enumerate(results, 1):
        rows += f"""
        <tr>
          <td class="rank">{i}</td>
          <td class="name">
            <a href="{r['yelp_url']}" target="_blank">{r['name']}</a>
          </td>
          <td class="rating">
            <span class="stars">{stars(r['rating'])}</span>
            <span class="num">{r['rating']}</span>
            <span class="count">({r['review_count']})</span>
          </td>
          <td class="location">{r['city']}</td>
          <td>{r['address']}</td>
          <td>{r['phone']}</td>
          <td>{anthem_badge(r['anthem'])}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Top PT Physicians — Bay Area / Anthem</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          background: #f4f6f8; color: #1a1a2e; }}
  .header {{ background: #1a1a2e; color: #fff; padding: 1.75rem 2.5rem; }}
  .header h1 {{ font-size: 1.5rem; margin-bottom: .3rem; }}
  .header p  {{ font-size: .85rem; opacity: .65; }}
  .notice {{ margin: 1.25rem 2rem; padding: .9rem 1.2rem;
             background: #fff8e1; border-left: 4px solid #f9a825;
             border-radius: 4px; font-size: .88rem; line-height: 1.5; }}
  .container {{ padding: 1rem 2rem 3rem; overflow-x: auto; }}
  table {{ width: 100%; border-collapse: collapse; background: #fff;
           border-radius: 8px; overflow: hidden;
           box-shadow: 0 1px 6px rgba(0,0,0,.08); font-size: .88rem; }}
  th {{ background: #1a1a2e; color: #fff; padding: .75rem 1rem;
        text-align: left; font-weight: 600; white-space: nowrap; }}
  td {{ padding: .65rem 1rem; border-bottom: 1px solid #eee; vertical-align: middle; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #f0f4ff; }}
  .rank  {{ color: #999; font-size: .8rem; width: 36px; text-align: center; }}
  .name a {{ color: #1a1a2e; font-weight: 600; text-decoration: none; }}
  .name a:hover {{ text-decoration: underline; color: #3a7bd5; }}
  .stars {{ color: #f5a623; letter-spacing: .05em; }}
  .num   {{ font-weight: 700; margin-left: .35rem; }}
  .count {{ color: #999; font-size: .8rem; }}
  .badge {{ display: inline-block; font-size: .72rem; font-weight: 600;
            padding: .18em .55em; border-radius: 4px; white-space: nowrap; }}
  .confirmed  {{ background: #d4edda; color: #1a6b3c; }}
  .not-listed {{ background: #f0f0f0; color: #777; }}
  .unknown    {{ background: #fff3cd; color: #856404; }}
  .footer {{ text-align: center; font-size: .78rem; color: #aaa;
             padding: 1.5rem 0 2rem; }}
</style>
</head>
<body>
<div class="header">
  <h1>🏥 Top Physical Therapists — San Francisco Bay Area</h1>
  <p>Sorted by Yelp rating · Anthem insurance check via Healthgrades · Generated {generated}</p>
</div>
<div class="notice">
  <strong>Insurance note:</strong> "Anthem listed" means the provider appeared on Healthgrades
  when filtering for Anthem Blue Cross. Always call the office to confirm your specific plan
  (PPO / HMO / EPO) is accepted before booking.
</div>
<div class="container">
<table>
  <thead>
    <tr>
      <th>#</th><th>Provider</th><th>Rating</th>
      <th>City</th><th>Address</th><th>Phone</th><th>Anthem</th>
    </tr>
  </thead>
  <tbody>{rows}</tbody>
</table>
</div>
<div class="footer">Data from Yelp Fusion API + Healthgrades · {generated}</div>
</body>
</html>"""


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not YELP_API_KEY:
        print("ERROR: Set your Yelp API key first:")
        print("  export YELP_API_KEY=your-key-here")
        print("  Get a free key at: https://fusion.yelp.com")
        sys.exit(1)

    results = collect_yelp(YELP_API_KEY)
    anthem_names = healthgrades_anthem_names()
    results = flag_anthem(results, anthem_names)

    # Sort: Anthem-confirmed first, then by rating desc, then review count desc
    results.sort(key=lambda r: (
        0 if r["anthem"] is True else 1,
        -r["rating"],
        -r["review_count"],
    ))

    generated = datetime.now().strftime("%B %d, %Y %H:%M")
    html = build_html(results, generated)

    out = os.path.join(os.path.expanduser("~"), "Downloads", "bay_area_pt_anthem.html")
    with open(out, "w") as f:
        f.write(html)

    print(f"Found {len(results)} providers. Saved to:\n  {out}")
    print(f"\nOpen with:\n  open \"{out}\"")


if __name__ == "__main__":
    main()
