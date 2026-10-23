#!/usr/bin/env python3
"""
Read/write the Photos.app library via AppleScript (osascript). No API, no auth —
works because Photos.app is signed in locally. Everything here shells out to `osascript`;
this file just builds the AppleScript text and handles escaping/indexing consistently.

Subcommands:
  list-albums
  list        --album NAME
  count       --album NAME
  export      --album NAME --out DIR [--start N] [--end M]   # 1-indexed, inclusive; omit both = all
  import      --file PATH [--album NAME] [--date "October 24, 2020 2:17:17 PM"]
  set-date    --album NAME --filename NAME --date "October 24, 2020 2:17:17 PM"

Examples:
  python3 photos.py list-albums
  python3 photos.py list --album Vacation
  python3 photos.py export --album Vacation --out ~/Pictures/export --start 60 --end 76
  python3 photos.py import --file ~/Pictures/retouched.jpg --album Vacation --date "October 24, 2020 2:17:17 PM"
  python3 photos.py set-date --album Vacation --filename retouched.jpg --date "October 24, 2020 2:17:17 PM"
"""
import argparse
import subprocess
import sys


def run_applescript(script: str) -> str:
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"osascript error:\n{result.stderr}")
    return result.stdout.strip()


def esc(s: str) -> str:
    """Escape a string for embedding inside a double-quoted AppleScript literal."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def list_albums():
    out = run_applescript('tell application "Photos" to get name of every album')
    for name in out.split(", "):
        print(name)


def list_items(album: str):
    script = f'''
    tell application "Photos"
        set theAlbum to album "{esc(album)}"
        set mediaItems to media items of theAlbum
        set outputList to {{}}
        set i to 0
        repeat with theItem in mediaItems
            set i to i + 1
            set end of outputList to (i as string) & "\\t" & (filename of theItem) & "\\t" & (date of theItem as string)
        end repeat
        set AppleScript's text item delimiters to linefeed
        set outStr to outputList as string
        set AppleScript's text item delimiters to ""
        return outStr
    end tell
    '''
    print(run_applescript(script))


def count_items(album: str):
    script = f'tell application "Photos" to get count of media items of album "{esc(album)}"'
    print(run_applescript(script))


def export_items(album: str, out_dir: str, start: int | None, end: int | None):
    import os
    os.makedirs(os.path.expanduser(out_dir), exist_ok=True)
    range_clause = ""
    if start or end:
        range_clause = f'''
        set startIdx to {start or 1}
        set endIdx to {end or "n"}
        if endIdx is "n" then set endIdx to n
        '''
    else:
        range_clause = "set startIdx to 1\n        set endIdx to n"
    script = f'''
    tell application "Photos"
        set theAlbum to album "{esc(album)}"
        set mediaItems to media items of theAlbum
        set n to count of mediaItems
        {range_clause}
        set exportFolder to POSIX file "{esc(os.path.expanduser(out_dir))}"
        set batchItems to {{}}
        repeat with i from startIdx to endIdx
            set end of batchItems to item i of mediaItems
        end repeat
        export batchItems to exportFolder
    end tell
    '''
    run_applescript(script)
    print(f"exported to {out_dir}")


def import_item(file_path: str, album: str | None, date: str | None):
    import os
    posix_path = os.path.abspath(os.path.expanduser(file_path))
    date_line = f'set date of itm to date "{esc(date)}"' if date else ""
    # Omitting the album imports straight into the library (it lands in Recents),
    # which is what you want for a one-off that doesn't belong in a collection.
    into_clause = f' into album "{esc(album)}"' if album else ""
    script = f'''
    tell application "Photos"
        set importedItems to import {{POSIX file "{esc(posix_path)}"}}{into_clause} skip check duplicates true
        repeat with itm in importedItems
            {date_line}
            return {{filename of itm, date of itm as string}}
        end repeat
    end tell
    '''
    print(run_applescript(script))


def set_date(album: str, filename: str, date: str):
    script = f'''
    tell application "Photos"
        set theAlbum to album "{esc(album)}"
        set mediaItems to media items of theAlbum
        repeat with itm in mediaItems
            if filename of itm is "{esc(filename)}" then
                set date of itm to date "{esc(date)}"
                return {{filename of itm, date of itm as string}}
            end if
        end repeat
        return "not found: {esc(filename)}"
    end tell
    '''
    print(run_applescript(script))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list-albums")

    p = sub.add_parser("list")
    p.add_argument("--album", required=True)

    p = sub.add_parser("count")
    p.add_argument("--album", required=True)

    p = sub.add_parser("export")
    p.add_argument("--album", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--start", type=int, default=None)
    p.add_argument("--end", type=int, default=None)

    p = sub.add_parser("import")
    p.add_argument("--file", required=True)
    p.add_argument("--album", default=None, help="omit to import into the library (Recents)")
    p.add_argument("--date", default=None)

    p = sub.add_parser("set-date")
    p.add_argument("--album", required=True)
    p.add_argument("--filename", required=True)
    p.add_argument("--date", required=True)

    args = ap.parse_args()
    if args.cmd == "list-albums":
        list_albums()
    elif args.cmd == "list":
        list_items(args.album)
    elif args.cmd == "count":
        count_items(args.album)
    elif args.cmd == "export":
        export_items(args.album, args.out, args.start, args.end)
    elif args.cmd == "import":
        import_item(args.file, args.album, args.date)
    elif args.cmd == "set-date":
        set_date(args.album, args.filename, args.date)


if __name__ == "__main__":
    main()
