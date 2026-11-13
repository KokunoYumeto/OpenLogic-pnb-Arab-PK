"""Export and validate one vector SVG per page of the guarded diagram build."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import fitz
from lxml import etree


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("directory", type=Path)
    cli.add_argument("--pdf", type=Path, required=True)
    cli.add_argument("--build-receipt", type=Path, required=True)
    args = cli.parse_args()
    root = args.directory
    inventory = json.loads((root / "WEB-FIGURE-PROJECTION.json").read_bytes())
    receipt = json.loads(args.build_receipt.read_bytes())
    pdf_hash = sha256(args.pdf.read_bytes()).hexdigest()
    if not receipt["acquired"] or receipt["status"] != "diagnostic_rendered":
        raise ValueError("Diagram PDF has no successful guarded build receipt.")
    runs = [x for x in receipt["processes"] if x.get("pdf_sha256") == pdf_hash]
    if len(runs) != 1 or runs[0]["errors"] or runs[0]["missing_characters"]:
        raise ValueError("Diagram PDF and TeX log must match the successful guarded build.")
    dest = root / "diagram-assets"
    dest.mkdir(exist_ok=True)
    result = []
    with fitz.open(args.pdf) as pdf:
        if len(pdf) != inventory["figures"]:
            raise ValueError(f"Expected {inventory['figures']} diagram pages, got {len(pdf)}.")
        for page, item in zip(pdf, inventory["figures_by_order"], strict=True):
            # Drawings and visible text form the original figure's bounds.
            bounds = fitz.Rect()
            for drawing in page.get_drawings():
                bounds.include_rect(drawing["rect"])
            for word in page.get_text("words"):
                bounds.include_rect(fitz.Rect(word[:4]))
            if bounds.is_empty:
                raise ValueError(f"No artwork in {item['id']}")
            bounds = (bounds + (-7, -7, 7, 7)) & page.rect
            if bounds.is_empty:
                raise ValueError(f"Empty diagram crop in {item['id']}")
            svg = etree.fromstring(page.get_svg_image(text_as_path=True).encode())
            if svg.xpath("//*[local-name()='image' or local-name()='script']"):
                raise ValueError(f"Raster or executable payload in vector diagram {item['id']}")
            svg.set("viewBox", " ".join(format(v, ".5f") for v in (bounds.x0, bounds.y0, bounds.width, bounds.height)))
            svg.set("width", format(bounds.width, ".5f"))
            svg.set("height", format(bounds.height, ".5f"))
            data = etree.tostring(svg, encoding="utf-8", xml_declaration=True)
            output = dest / (item["id"] + ".svg")
            output.write_bytes(data)
            result.append({"id": item["id"], "source_sha256": item["sha256"],
                           "sha256": sha256(data).hexdigest(), "bytes": len(data)})
    data = {"pdf_sha256": pdf_hash, "vector_svgs": len(result), "artifacts": result}
    (root / "WEB-DIAGRAM-EXPORT.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf8")
    print(f"Exported {len(result)} vector SVGs.")


if __name__ == "__main__":
    main()
