#!/usr/bin/env python3
"""Download the 12 project videos using only the Python standard library."""

import argparse
import hashlib
import http.client
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
CHUNK_SIZE = 1024 * 1024


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def matches(path, entry):
    return (
        path.is_file()
        and path.stat().st_size == entry["size"]
        and sha256(path) == entry["sha256"]
    )


def read_manifest(path):
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("version") != 1:
        raise ValueError("Unsupported manifest version")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("Manifest must contain a nonempty files list")
    seen = set()
    for entry in files:
        name = entry["path"]
        relative = PurePosixPath(name)
        if (not name or relative.is_absolute() or ".." in relative.parts
                or "\\" in name or ":" in name or relative.as_posix() != name
                or relative.suffix != ".mp4" or name in seen):
            raise ValueError(f"Invalid or duplicate video path: {name}")
        seen.add(name)
        if type(entry["size"]) is not int or entry["size"] <= 0:
            raise ValueError(f"Invalid file size: {name}")
        if not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]):
            raise ValueError(f"Invalid SHA-256: {name}")
    return manifest


def source_url(entry, base_url):
    url = (base_url.rstrip("/") + "/" + urllib.parse.quote(entry["path"], safe="/")) if base_url else entry.get("url")
    if not url:
        raise ValueError("No download source configured. Supply --base-url or set each file's url in the manifest.")
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"Download source must be an HTTP(S) URL for {entry['path']}")
    return url


def download(entry, target, url, timeout):
    """Keep partial bytes after interruption; install only a verified complete file."""
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    if partial.exists() and partial.stat().st_size >= entry["size"]:
        if matches(partial, entry):
            partial.replace(target)
            return
        partial.unlink()
    offset = partial.stat().st_size if partial.exists() else 0
    headers = {"User-Agent": "Aletheia-dataset-downloader/1", "Accept-Encoding": "identity"}
    if offset:
        headers["Range"] = f"bytes={offset}-"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status == 206:
            expected = f"bytes {offset}-{entry['size'] - 1}/{entry['size']}"
            if response.headers.get("Content-Range") != expected:
                raise ValueError("Server returned an unexpected Content-Range")
        elif response.status == 200:
            # Some hosts ignore Range; restart instead of appending duplicate bytes.
            offset = 0
        else:
            raise ValueError(f"Unexpected HTTP status: {response.status}")
        length = response.headers.get("Content-Length")
        if length is not None and int(length) != entry["size"] - offset:
            raise ValueError("Server file size differs from the manifest")
        downloaded = offset
        last_report = time.monotonic()
        with partial.open("ab" if offset else "wb") as stream:
            while True:
                chunk = response.read(CHUNK_SIZE)
                if not chunk:
                    break
                downloaded += len(chunk)
                if downloaded > entry["size"]:
                    raise ValueError("Server sent more bytes than expected")
                stream.write(chunk)
                if time.monotonic() - last_report >= 5:
                    print(f"  {downloaded / entry['size']:.0%}", flush=True)
                    last_report = time.monotonic()
    if partial.stat().st_size != entry["size"]:
        raise ValueError("Incomplete response; partial file retained for resume")
    if not matches(partial, entry):
        partial.unlink()
        raise ValueError("SHA-256 mismatch; discarded corrupt download")
    partial.replace(target)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "datasets/manifest.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "CrossSight/dataset")
    parser.add_argument("--base-url", help="HTTP(S) root containing day_01/ and day_02/; overrides manifest URLs")
    parser.add_argument("--verify-only", action="store_true", help="Verify local files without downloading")
    parser.add_argument("--list", action="store_true", help="List expected videos without downloading")
    parser.add_argument("--retries", type=int, default=3, help="Maximum attempts per file (default: 3)")
    parser.add_argument("--timeout", type=float, default=60, help="Socket timeout in seconds (default: 60)")
    args = parser.parse_args(argv)
    if args.retries < 1 or args.timeout <= 0:
        parser.error("--retries and --timeout must be positive")
    try:
        manifest = read_manifest(args.manifest)
        files = manifest["files"]
        print(f"{len(files)} videos, {sum(e['size'] for e in files) / 1024**2:.1f} MiB", flush=True)
        if args.list:
            for entry in files:
                print(f"{entry['path']}  {entry['size']} bytes  sha256={entry['sha256']}")
            return 0
        output = args.output_dir.resolve()
        pending = []
        for entry in files:
            target = output.joinpath(*PurePosixPath(entry["path"]).parts)
            # Refuse existing symlinks that could redirect writes outside the output.
            for candidate in (target, target.with_name(target.name + ".part")):
                if not candidate.resolve().is_relative_to(output):
                    raise ValueError(f"Path escapes output directory: {candidate}")
            if matches(target, entry):
                print(f"OK    {entry['path']}", flush=True)
            else:
                pending.append((entry, target))
        if args.verify_only:
            for entry, _ in pending:
                print(f"MISSING/INVALID  {entry['path']}")
            return 1 if pending else 0
        base_url = args.base_url or manifest.get("base_url")
        # Check all sources before starting a potentially large download.
        downloads = [(entry, target, source_url(entry, base_url)) for entry, target in pending]
        failed = 0
        for entry, target, url in downloads:
            for attempt in range(1, args.retries + 1):
                print(f"GET   {entry['path']} (attempt {attempt}/{args.retries})", flush=True)
                try:
                    download(entry, target, url, args.timeout)
                    print(f"OK    {entry['path']}", flush=True)
                    break
                except (OSError, ValueError, http.client.HTTPException) as exc:
                    print(f"  {exc}", file=sys.stderr, flush=True)
                    if attempt == args.retries:
                        failed += 1
                    else:
                        time.sleep(min(attempt, 3))
        if failed:
            print(f"{failed} video(s) failed. Run the same command to retry/resume.", file=sys.stderr)
            return 1
        print(f"All {len(files)} videos verified in {output}")
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted. Run the same command to resume.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
