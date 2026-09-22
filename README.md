# Likewise/Pix → Letterboxd Export

Converts a JSON export pulled from the Likewise/Pix API into a CSV you can
import into Letterboxd.

## 1. Get your data from Likewise/Pix

Likewise doesn't have a public export feature or API, so you'll need to pull
your data from the same endpoint the Pix website uses:

1. Log into your profile at `pix-media.com` in a browser.
2. Open dev tools (F12) → **Network** tab → filter by **Fetch/XHR**.
3. Reload your profile page and find the request that returns your feed
   data (JSON response containing your rated titles).
4. Copy that request as a `curl` command (most browsers offer this via
   right-click → Copy → Copy as cURL).
5. Run the curl command and save the output to a file, e.g.:

   ```
   curl '<the request URL>' -H '<headers...>' -o likewise_response.json
   ```

**Pagination note:** a single response only covers one page of your
history. The response includes a `next` object with cursor values like
`itemsBefore` and `listsBefore` — repeat the curl request using those
values (swapped into the query string) to page backward through your full
history, and combine all the responses' `feed` arrays before running the
script. If you only care about your most recent activity, one page may be
enough.

## 2. Run the conversion script

```
python3 convert_to_letterboxd.py likewise_response.json
```

This produces two files:

| File | What's in it |
|---|---|
| `letterboxd_movies.csv` | Movies, formatted for Letterboxd's importer |
| `shows_not_imported.csv` | TV shows found in your data — kept as a record, since Letterboxd doesn't support TV |

The script pulls titles from both your main feed and any custom lists,
dedupes movies that appear in more than one place, and maps fields to
Letterboxd's expected columns (`Title`, `Year`, `tmdbID`, `WatchedDate`,
`Rating`).

## 3. Import into Letterboxd

1. Go to [letterboxd.com/import](https://letterboxd.com/import).
2. Upload `letterboxd_movies.csv`.
3. Choose whether it should import as watched films, diary entries, or go
   to a list/your watchlist.
4. Review the match preview — titles with a `tmdbID` should match exactly;
   anything without one is a best-guess title/year match, so double-check
   those before confirming.

## Notes

- Ratings carry over as-is (both platforms use a 0.5–5 star scale).
- `WatchedDate` is only filled in for titles marked as watched (`doneIt`);
  anything not yet watched will have this left blank.
- If a title has no TMDB id, Letterboxd will try to match it by title and
  year alone — check the import preview for mismatches before finishing.
