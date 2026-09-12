"""Bounded anonymous HTTP check for the HTTPS links embedded in the Sets EPUB."""
from __future__ import annotations

import argparse
import hashlib
import json
import ssl
import urllib.error
import urllib.request
from pathlib import Path


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qa", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    qa_bytes = args.qa.read_bytes()
    qa = json.loads(qa_bytes.decode("utf-8-sig"))
    urls = qa["links"]["external_https_links"]
    context = ssl.create_default_context()
    rows = []
    for url in urls:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "OpenLogic-pnb-Arab-PK-EPUB-link-check/0.2 (+https://github.com/KokunoYumeto/OpenLogic-pnb-Arab-PK)"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=30, context=context) as response:
                prefix = response.read(1024)
                rows.append(
                    {
                        "url": url,
                        "status": response.status,
                        "final_url": response.geturl(),
                        "content_type": response.headers.get_content_type(),
                        "content_length_header": response.headers.get("Content-Length"),
                        "sample_bytes": len(prefix),
                        "sample_sha256": sha(prefix),
                        "pass": 200 <= response.status < 400,
                    }
                )
        except (urllib.error.URLError, TimeoutError) as error:
            rows.append({"url": url, "pass": False, "error": str(error)})
    failures = [row for row in rows if not row["pass"]]
    report = {
        "schema": "pnb-sets-epub3-external-link-qa/1",
        "status": "pass" if not failures else "fail",
        "mode": "anonymous bounded GET; first 1024 response bytes read; redirects followed; no credentials",
        "input_qa": {"path": str(args.qa.resolve()), "bytes": len(qa_bytes), "sha256": sha(qa_bytes)},
        "links_checked": len(rows),
        "links_passed": len(rows) - len(failures),
        "links_failed": len(failures),
        "results": rows,
    }
    payload = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)
    print(json.dumps({"status": report["status"], "links_checked": len(rows), "links_failed": len(failures), "output": {"path": str(args.output.resolve()), "bytes": len(payload), "sha256": sha(payload)}}, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
