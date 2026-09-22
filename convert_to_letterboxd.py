"""
Convert a Likewise/Pix feed export (JSON) into Letterboxd-import-ready CSVs.

Usage:
    python3 convert_to_letterboxd.py likewise_response_all.json

Produces two files:
    letterboxd_movies.csv   -> movies, ready to import at letterboxd.com/import
    shows_not_imported.csv  -> TV shows found in the data (Letterboxd has no
                                TV support, so these are just logged for you)

How it works, step by step:
1. Load the JSON and grab the "feed" list.
2. Walk every entry. If it's type "item", it's a single title -> handle
   it directly. If it's type "list", it's a custom list with its own
   nested "items" array -> walk into that array too, since movies you've
   rated can show up inside custom lists as well as the main feed.
3. For each title found, decide if it's a Movie or a Show:
     - top-level items use source["itemCategory"]
     - items nested inside a list use item["categories"] (a list)
4. Deduplicate by TMDB id, since the same movie can appear both in the
   main feed AND inside a custom list -> we only want it once in the CSV.
5. Write out Letterboxd's expected columns: Title, Year, tmdbID,
   WatchedDate, Rating.
"""

import json
import csv
import sys
from datetime import datetime

def get_year(release_date_str):
    """Pull just the year out of an ISO date string like '1987-06-03T00:00:00.000Z'."""
    if not release_date_str:
        return ""
    return release_date_str[:4]

def get_watched_date(done_it_date_str):
    """Convert ISO datetime to the plain YYYY-MM-DD Letterboxd wants."""
    if not done_it_date_str:
        return ""
    try:
        return datetime.fromisoformat(done_it_date_str.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except ValueError:
        return ""

def normalize_entry(title, category, release_date, done_it_date, rating,
                     third_party_id, third_party_provider, done_it):
    """Turn the raw fields we pulled out into one clean dict."""
    return {
        "Title": title,
        "Year": get_year(release_date),
        "tmdbID": third_party_id if third_party_provider == "TMDB" else "",
        "WatchedDate": get_watched_date(done_it_date) if done_it else "",
        "Rating": rating if rating is not None else "",
        "_category": category,       # internal use only, not written to CSV
        "_done_it": bool(done_it),   # internal use only, not written to CSV
    }

def walk_feed(feed):
    """Yield a normalized dict for every title found, top-level or nested in lists."""
    for entry in feed:
        entry_type = entry.get("type")

        if entry_type == "item":
            src = entry.get("source", {})
            yield normalize_entry(
                title=src.get("title"),
                category=src.get("itemCategory"),
                release_date=src.get("releaseDate"),
                done_it_date=src.get("doneItDate"),
                rating=src.get("rating"),
                third_party_id=src.get("thirdPartyId"),
                third_party_provider=src.get("thirdPartyProvider"),
                done_it=src.get("doneIt"),
            )

        elif entry_type == "list":
            src = entry.get("source", {})
            for item in src.get("items", []):
                categories = item.get("categories", [])
                # A nested item can be tagged with both "Movies" and "Shows";
                # treat it as a Show only if it's Shows and NOT Movies.
                category = "Shows" if ("Shows" in categories and "Movies" not in categories) else "Movies"
                yield normalize_entry(
                    title=item.get("title"),
                    category=category,
                    release_date=item.get("releaseDate"),
                    done_it_date=item.get("doneItDate"),
                    rating=item.get("rating"),
                    third_party_id=item.get("thirdPartyId"),
                    third_party_provider=item.get("thirdPartyProvider"),
                    done_it=item.get("doneIt"),
                )

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 convert_to_letterboxd.py <path-to-json>")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        data = json.load(f)

    feed = data.get("feed", [])

    seen_movie_ids = set()
    seen_show_ids = set()
    movies = []
    shows = []

    for entry in walk_feed(feed):
        if not entry["Title"]:
            continue  # skip anything with no title, just in case

        dedupe_key = entry["tmdbID"] or entry["Title"]  # fall back to title if no tmdbID

        if entry["_category"] == "Movies":
            if dedupe_key in seen_movie_ids:
                continue
            seen_movie_ids.add(dedupe_key)
            movies.append(entry)
        else:
            if dedupe_key in seen_show_ids:
                continue
            seen_show_ids.add(dedupe_key)
            shows.append(entry)

    # Write the Letterboxd-ready movie CSV
    with open("letterboxd_movies.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Title", "Year", "tmdbID", "WatchedDate", "Rating"])
        writer.writeheader()
        for m in movies:
            writer.writerow({k: v for k, v in m.items() if not k.startswith("_")})

    # Write the shows to a separate file just so you have a record of them
    with open("shows_not_imported.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Title", "Year", "tmdbID", "WatchedDate", "Rating"])
        writer.writeheader()
        for s in shows:
            writer.writerow({k: v for k, v in s.items() if not k.startswith("_")})

    print(f"Wrote {len(movies)} movies to letterboxd_movies.csv")
    print(f"Wrote {len(shows)} TV shows to shows_not_imported.csv (Letterboxd can't import these)")

if __name__ == "__main__":
    main()
