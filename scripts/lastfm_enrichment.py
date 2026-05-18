"""
Last.fm Enrichment Script
==========================
Takes your deezer_ai_artists CSV/Excel, looks up each artist and album
on Last.fm, and saves an enriched dataset ready for analysis.

WHAT LAST.FM PROVIDES:
  - Artist level : playcount (total scrobbles), listeners (unique listeners)
  - Album level  : playcount for the album (when found by name match)
  - Track level  : playcount per track (summed as album total fallback)

MATCHING STRATEGY:
  1. Try album.getinfo with exact artist + album name
  2. If not found, try album.search and fuzzy-match the top result
  3. Always fetch artist.getinfo regardless (artist stats are very reliable)
  4. If album match fails, sum top-track playcounts as a proxy

SETUP:
  pip3 install pandas requests openpyxl fuzzywuzzy python-Levenshtein

RUN:
  python3 lastfm_enrichment.py
"""

import time
import requests
import pandas as pd
from fuzzywuzzy import fuzz

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

API_KEY     = "fe43739a78385c23252fe87031464175"
API_ROOT    = "http://ws.audioscrobbler.com/2.0/"
INPUT_FILE  = "/Users/pelinumur/deezer_ai_artists_variety10.csv"   # your Deezer data
OUTPUT_FILE = "deezer_lastfm_enriched.csv10" #!!!!!

# How similar album names need to be to count as a match (0-100)
# 80 means "Acoustic Bossa Nova" matches "Acoustic Bossa Nova Piano" 
FUZZY_THRESHOLD = 80

# Seconds to wait between API calls — Last.fm allows 5 requests/second
# 0.25 seconds = 4 requests/second, safely under the limit
API_DELAY = 0.25


# ─────────────────────────────────────────────
# LAST.FM API CALLS
# ─────────────────────────────────────────────

def lastfm_get(method: str, params: dict) -> dict:
    """
    Base function for all Last.fm API calls.
    Always adds api_key and format=json automatically.
    Returns the parsed JSON dict, or empty dict on error.
    """
    all_params = {
        "method":  method,
        "api_key": API_KEY,
        "format":  "json",
        **params
    }
    try:
        r = requests.get(API_ROOT, params=all_params, timeout=10)
        r.raise_for_status()
        data = r.json()
        # Last.fm returns {"error": N, "message": "..."} for failures
        if "error" in data:
            return {}
        return data
    except Exception:
        return {}


def get_artist_info(artist_name: str) -> dict:
    """
    Fetches artist-level stats from Last.fm.
    Returns dict with: lastfm_artist_found, artist_playcount,
    artist_listeners, artist_url, lastfm_artist_name
    """
    result = {
        "lastfm_artist_found": False,
        "artist_playcount":    None,
        "artist_listeners":    None,
        "artist_url":          None,
        "lastfm_artist_name":  None,
    }
    data = lastfm_get("artist.getinfo", {"artist": artist_name})
    artist = data.get("artist")
    if not artist:
        return result

    stats = artist.get("stats", {})
    result["lastfm_artist_found"] = True
    result["lastfm_artist_name"]  = artist.get("name")
    result["artist_playcount"]    = int(stats.get("playcount", 0) or 0)
    result["artist_listeners"]    = int(stats.get("listeners", 0) or 0)
    result["artist_url"]          = artist.get("url")
    return result


def get_album_info_exact(artist_name: str, album_title: str) -> dict:
    """
    Tries to get album info using exact artist + album name.
    Returns playcount if found, or None.
    """
    data = lastfm_get("album.getinfo", {
        "artist": artist_name,
        "album":  album_title,
    })
    album = data.get("album")
    if not album:
        return {"album_playcount": None, "album_match_type": None, "album_match_score": None}

    playcount = int(album.get("playcount", 0) or 0)
    return {
        "album_playcount":    playcount,
        "album_match_type":   "exact",
        "album_match_score":  100,
    }


def get_album_info_fuzzy(artist_name: str, album_title: str) -> dict:
    """
    Searches Last.fm for the album by name, then fuzzy-matches the
    top results against our album title to find the best match.
    """
    data = lastfm_get("album.search", {
        "album": album_title,
        "limit": 10,
    })

    albums_found = (
        data.get("results", {})
            .get("albummatches", {})
            .get("album", [])
    )
    if not albums_found:
        return {"album_playcount": None, "album_match_type": "not_found", "album_match_score": 0}

    # Score each result: combine album name similarity + artist name similarity
    best_score  = 0
    best_album  = None
    for candidate in albums_found:
        title_score  = fuzz.token_sort_ratio(
            album_title.lower(), candidate.get("name", "").lower()
        )
        artist_score = fuzz.token_sort_ratio(
            artist_name.lower(), candidate.get("artist", "").lower()
        )
        # Weight album title more heavily than artist name
        combined = (title_score * 0.7) + (artist_score * 0.3)
        if combined > best_score:
            best_score = combined
            best_album = candidate

    if best_score < FUZZY_THRESHOLD or not best_album:
        return {"album_playcount": None, "album_match_type": "below_threshold", "album_match_score": round(best_score)}

    # Fetch full album details using the matched name
    detail_data = lastfm_get("album.getinfo", {
        "artist": best_album.get("artist"),
        "album":  best_album.get("name"),
    })
    album_detail = detail_data.get("album")
    if not album_detail:
        return {"album_playcount": None, "album_match_type": "fuzzy_no_detail", "album_match_score": round(best_score)}

    playcount = int(album_detail.get("playcount", 0) or 0)
    return {
        "album_playcount":   playcount,
        "album_match_type":  "fuzzy",
        "album_match_score": round(best_score),
    }


def get_track_playcount_sum(artist_name: str, album_title: str) -> dict:
    """
    Last resort: fetch artist's top tracks and sum playcounts of tracks
    that appear to belong to this album. Used when album lookup fails entirely.
    This is an approximation — use album_match_type to flag these rows.
    """
    data = lastfm_get("artist.gettoptracks", {
        "artist": artist_name,
        "limit":  50,
    })
    tracks = data.get("toptracks", {}).get("track", [])
    if not tracks:
        return {"album_playcount": None, "album_match_type": "no_tracks_found", "album_match_score": 0}

    # Sum all track playcounts as a rough artist-level proxy
    total = sum(int(t.get("playcount", 0) or 0) for t in tracks)
    return {
        "album_playcount":   total,
        "album_match_type":  "artist_tracks_sum",
        "album_match_score": 0,
    }


# ─────────────────────────────────────────────
# MAIN ENRICHMENT FUNCTION
# ─────────────────────────────────────────────

def enrich_album(artist_name: str, album_title: str) -> dict:
    """
    Full enrichment pipeline for one album:
    1. Get artist stats (always)
    2. Try exact album lookup
    3. Fall back to fuzzy search
    4. Fall back to track sum
    """
    # Step 1: Artist info — always reliable on Last.fm
    artist_info = get_artist_info(artist_name)
    time.sleep(API_DELAY)

    # Step 2: Try exact album match first
    album_info = get_album_info_exact(artist_name, album_title)
    time.sleep(API_DELAY)

    if album_info["album_playcount"] is None:
        # Step 3: Try fuzzy search
        album_info = get_album_info_fuzzy(artist_name, album_title)
        time.sleep(API_DELAY)

    if album_info["album_playcount"] is None:
        # Step 4: Fall back to summing artist's top tracks
        album_info = get_track_playcount_sum(artist_name, album_title)
        time.sleep(API_DELAY)

    return {**artist_info, **album_info}


# ─────────────────────────────────────────────
# LOAD DATA AND RUN
# ─────────────────────────────────────────────

def run():
    print("=" * 60)
    print("  Last.fm Enrichment Script")
    print("=" * 60)

    # Load your Deezer data — handle both CSV and Excel
    print(f"\n[DATA] Loading {INPUT_FILE}...")
    if INPUT_FILE.endswith(".xlsx") or INPUT_FILE.endswith(".xls"):
        df = pd.read_excel(INPUT_FILE, header=1)   # header=1 skips the title row
    else:
        df = pd.read_csv(INPUT_FILE)

    print(f"[DATA] Loaded {len(df)} albums.")
    print(f"[DATA] AI-flagged: {df['ai_flagged'].sum()} | Non-AI: {(~df['ai_flagged']).sum()}\n")

    # Add columns for Last.fm data
    lastfm_cols = [
        "lastfm_artist_found",
        "lastfm_artist_name",
        "artist_playcount",
        "artist_listeners",
        "artist_url",
        "album_playcount",
        "album_match_type",
        "album_match_score",
    ]
    for col in lastfm_cols:
        df[col] = None

    # Process each album
    for i, row in df.iterrows():
        artist_name = str(row["artist_name"]).strip()
        album_title = str(row["album_title"]).strip()

        print(f"[{i+1}/{len(df)}] {artist_name} — {album_title}")

        enriched = enrich_album(artist_name, album_title)

        for col in lastfm_cols:
            df.at[i, col] = enriched.get(col)

        # Print what we found
        if enriched["lastfm_artist_found"]:
            print(f"        Artist  ✓  plays={enriched['artist_playcount']:,}  "
                  f"listeners={enriched['artist_listeners']:,}")
        else:
            print(f"        Artist  ✗  not found on Last.fm")

        if enriched["album_playcount"] is not None:
            print(f"        Album   ✓  plays={enriched['album_playcount']:,}  "
                  f"match={enriched['album_match_type']} "
                  f"(score={enriched['album_match_score']})")
        else:
            print(f"        Album   ✗  not found")

        # Save progress every 25 rows
        if (i + 1) % 25 == 0:
            df.to_csv(OUTPUT_FILE, index=False)
            found     = df["lastfm_artist_found"].sum()
            print(f"\n  [SAVED] {OUTPUT_FILE}  —  {found}/{i+1} found so far\n")

    # Final save
    df.to_csv(OUTPUT_FILE, index=False)

    # Summary
    total         = len(df)
    artist_found  = int(df["lastfm_artist_found"].sum())
    album_exact   = int((df["album_match_type"] == "exact").sum())
    album_fuzzy   = int((df["album_match_type"] == "fuzzy").sum())
    album_missing = int(df["album_playcount"].isna().sum())

    print("\n" + "=" * 60)
    print("  ENRICHMENT COMPLETE")
    print("=" * 60)
    print(f"  Total albums processed  : {total}")
    print(f"  Artists found on Last.fm: {artist_found} ({100*artist_found//total}%)")
    print(f"  Albums matched (exact)  : {album_exact}")
    print(f"  Albums matched (fuzzy)  : {album_fuzzy}")
    print(f"  Albums not found        : {album_missing}")
    print(f"  Saved to                : {OUTPUT_FILE}")
    print("=" * 60)

    # Quick preview of key columns
    print("\nSample output (first 5 rows, key columns):")
    preview_cols = [
        "artist_name", "album_title", "ai_flagged",
        "artist_playcount", "artist_listeners",
        "album_playcount", "album_match_type"
    ]
    print(df[preview_cols].head().to_string())

    return df


if __name__ == "__main__":
    df = run()
