"""Package the cumulative semantic HTML as a chapter-spined EPUB 3."""

import argparse
from collections import Counter
from hashlib import sha256
import json
import mimetypes
from pathlib import Path, PurePosixPath
import re
from urllib.parse import quote, unquote, urlsplit
from uuid import NAMESPACE_URL, uuid5
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

from lxml import etree, html

from package_web_reader import LINKS, TITLE
from web_godel_delimiters import FONT_FILE
from web_modal_symbols import GPL_FILE, NOTICE_FILE


XHTML = "http://www.w3.org/1999/xhtml"
MATHML = "http://www.w3.org/1998/Math/MathML"
EPUB = "http://www.idpf.org/2007/ops"
OPF = "http://www.idpf.org/2007/opf"
DC = "http://purl.org/dc/elements/1.1/"
XML = "http://www.w3.org/XML/1998/namespace"
OCF = "urn:oasis:names:tc:opendocument:xmlns:container"
LANG = "pnb-Arab-PK"
PUBLISHER = "Open Logic Project"
MIMETYPE = b"application/epub+zip"
SOURCE_REVISION = "9620cc73f9c8e0ad003c514a5d3748f29611c4c0"
SUBJECT = "Logic"
FOOTNOTE_ROLES = {"doc-noteref": "noteref", "doc-endnotes": "endnotes"}
BIDI_CSS = re.compile(r"(?:direction|unicode-bidi)\s*:\s*(?:ltr|isolate)\s*;")


def tag(ns, name):
    return f"{{{ns}}}{name}"


def add(parent, ns, name, text=None, **attrs):
    child = etree.SubElement(parent, tag(ns, name), attrs)
    child.text = text
    return child


def serialize(tree):
    return etree.tostring(tree, encoding="utf-8", xml_declaration=True)


def xhtml_page(title):
    root = etree.Element(tag(XHTML, "html"), nsmap={None: XHTML, "epub": EPUB})
    root.set("lang", LANG)
    root.set(tag(XML, "lang"), LANG)
    root.set("dir", "rtl")
    head = add(root, XHTML, "head")
    add(head, XHTML, "title", title)
    add(head, XHTML, "link", rel="stylesheet", href="open-logic-pnb.css", type="text/css")
    return root, add(root, XHTML, "body")


def copy_markup(node, ns=XHTML):
    if not isinstance(node.tag, str):
        return etree.Comment(node.text or "")
    if node.tag == "math":
        ns = MATHML
    out = etree.Element(tag(ns, node.tag), nsmap={None: MATHML} if node.tag == "math" else None)
    for key, value in node.attrib.items():
        if key != "xmlns":
            out.set(key, value)
    if node.tag in ("math", "code", "pre") or node.get("lang") == "en" or "citation" in node.get("class", "").split():
        if out.get("dir") is None:
            out.set("dir", "ltr")
    if "citation-note" in node.get("class", "").split() and out.get("dir") is None:
        out.set("dir", "auto")
    if lang := out.get("lang"):
        out.set(tag(XML, "lang"), lang)
    if role := FOOTNOTE_ROLES.get(out.get("role")):
        out.set(tag(EPUB, "type"), role)
    out.text, out.tail = node.text, node.tail
    for child in node:
        out.append(copy_markup(child, ns))
    return out


def split_body(body):
    sections = [("front.xhtml", TITLE, [])]
    for node in body:
        key = node.get("id")
        if (node.tag in ("h1", "h2") and key) or key in ("footnotes", "bibliography"):
            if key == "footnotes":
                title = "حاشیے"
            else:
                heading = node.find("h2") if key == "bibliography" else node
                title = " ".join(" ".join(heading.xpath(".//text()[not(ancestor::annotation)]")).split())
            sections.append((f"section-{len(sections):03d}.xhtml", title, []))
        sections[-1][-1].append(node)
    return sections


def content_documents(tree):
    sections = split_body(tree.find("body"))
    documents, targets = {}, {}
    for name, title, nodes in sections:
        root, body = xhtml_page(title)
        for node in nodes:
            body.append(copy_markup(node))
        for key in root.xpath("//@id"):
            if key in targets:
                raise ValueError(f"Duplicate EPUB anchor {key}")
            targets[key] = name
        documents[name] = root

    def rewrite_links(page, document):
        for anchor in document.xpath("//x:a[starts-with(@href,'#')]", namespaces={"x": XHTML}):
            target = unquote(anchor.get("href")[1:])
            filename = targets[target]
            encoded = quote(target, safe=":-._~")
            anchor.set("href", (filename if page != filename else "") + "#" + encoded)

    for name, doc in documents.items():
        rewrite_links(name, doc)

    menu, nav_body = xhtml_page("فہرست")
    nav = copy_markup(tree.xpath("/html/body/header[1]/nav")[0])
    nav.set(tag(EPUB, "type"), "toc")
    nav.set("id", "toc")
    nav_body.append(nav)
    listing = nav.find(tag(XHTML, "ol"))
    for label, target in (("سرورق", "front.xhtml"), ("حاشیے", "#footnotes"), ("حوالیاں دی فہرست", "#bibliography")):
        item = add(listing, XHTML, "li")
        add(item, XHTML, "a", label, href=target)
        if target == "front.xhtml":
            listing.insert(0, item)
    rewrite_links("nav.xhtml", menu)
    documents["nav.xhtml"] = menu
    return documents


def publication_assets(directory, tree, diagnostic):
    css_name = "open-logic-pnb.css"
    css = (directory / css_name).read_text(encoding="utf-8")
    css = re.sub(r"(?m)^[^{}\n]+\{\s*\}\n?", "", BIDI_CSS.sub("", css))
    resources = {css_name: (css.encode(), "text/css")}
    font_links = set(re.findall(r'url\("([^"]+)"\)', css))
    images = set(tree.xpath("//img/@src"))
    figure_count = len(tree.xpath('//*[starts-with(@id,"diagram-") and .//img]'))
    if not diagnostic and figure_count != 70:
        raise ValueError(f"The cumulative reader requires all 70 diagrams; found {figure_count}.")
    for uri in sorted(font_links | images):
        path = PurePosixPath(uri)
        if path.is_absolute() or ".." in path.parts or path.parts[0] not in ("fonts", "diagrams"):
            raise ValueError(f"Unsupported EPUB resource {uri}")
        media = {".ttf": "font/ttf", ".otf": "font/otf"}.get(path.suffix) or mimetypes.guess_type(uri)[0]
        if media not in ("font/ttf", "font/otf", "image/svg+xml", "image/png", "image/jpeg"):
            raise ValueError(f"Unsupported EPUB resource type: {uri} {media}")
        resources[uri] = ((directory / path).read_bytes(), media)
    font_license_files = ("NOTICE.md", "OFL.txt", FONT_FILE.replace(".ttf", "-OFL.txt"), NOTICE_FILE, GPL_FILE)
    return resources, {name: (directory / "fonts" / name).read_text("utf-8") for name in font_license_files}, figure_count


def opf_package(documents, resources, book_id, modified, description):
    root = etree.Element(tag(OPF, "package"), nsmap={None: OPF, "dc": DC},
                         version="3.0", attrib={"unique-identifier": "book-id"})
    root.set(tag(XML, "lang"), LANG)
    metadata = add(root, OPF, "metadata")
    add(metadata, DC, "identifier", book_id, id="book-id")
    add(metadata, DC, "title", TITLE)
    add(metadata, DC, "language", LANG)
    add(metadata, DC, "creator", PUBLISHER)
    add(metadata, DC, "subject", SUBJECT)
    add(metadata, DC, "description", description)
    add(metadata, DC, "source", LINKS[1][1])
    add(metadata, DC, "rights", "Creative Commons Attribution 4.0 International. Embedded fonts: SIL Open Font License 1.1 and GNU GPL with the TX fonts document-embedding exception.")
    add(metadata, OPF, "meta", modified, property="dcterms:modified")
    manifest = add(root, OPF, "manifest")
    spine = add(root, OPF, "spine", **{"page-progression-direction": "rtl"})
    for index, (name, doc) in enumerate(documents.items()):
        properties = []
        if name == "nav.xhtml":
            properties.append("nav")
        if doc.find(".//" + tag(MATHML, "math")) is not None:
            properties.append("mathml")
        attrs = {"properties": " ".join(properties)} if properties else {}
        identifier = f"text-{index}"
        add(manifest, OPF, "item", id=identifier, href=name, **{"media-type": "application/xhtml+xml"}, **attrs)
        if name != "nav.xhtml":
            add(spine, OPF, "itemref", idref=identifier)
    for index, (name, (_, media)) in enumerate(resources.items()):
        add(manifest, OPF, "item", id=f"asset-{index}", href=name, **{"media-type": media})
    return root


def zip_entry(archive, name, data, method=ZIP_DEFLATED):
    entry = ZipInfo(name, (2026, 11, 13, 0, 0, 0))
    entry.create_system = 3
    entry.external_attr = 0o100644 << 16
    archive.writestr(entry, data, compress_type=method, compresslevel=9)


def audit_archive(path, source, source_ids, source_figures):
    ns = {"x": XHTML, "m": MATHML, "p": OPF, "e": EPUB}
    with ZipFile(path) as archive:
        items = archive.infolist()
        if items[0].filename != "mimetype" or items[0].compress_type != ZIP_STORED or archive.read("mimetype") != MIMETYPE:
            raise ValueError("Invalid EPUB mimetype entry")
        if error := archive.testzip():
            raise ValueError(f"EPUB CRC failure at {error}")
        opf = etree.fromstring(archive.read("EPUB/package.opf"))
        manifest = {item.get("id"): item for item in opf.xpath("//p:item", namespaces=ns)}
        filenames = set(archive.namelist())
        if filenames != {"mimetype", "META-INF/container.xml", "EPUB/package.opf"} | {
            "EPUB/" + item.get("href") for item in manifest.values()
        }:
            raise ValueError("Manifest and packaged entries differ")
        spine = opf.xpath("//p:itemref/@idref", namespaces=ns)
        docs = {i.get("href"): etree.fromstring(archive.read("EPUB/" + i.get("href")))
                for i in manifest.values() if i.get("media-type") == "application/xhtml+xml"}
        anchors = {name: set(doc.xpath("//@id")) for name, doc in docs.items()}
        ids = set().union(*anchors.values())
        if source_ids - ids:
            raise ValueError("EPUB dropped HTML anchors")
        if any(doc.get("dir") != "rtl" or doc.get("lang") != LANG for doc in docs.values()):
            raise ValueError("EPUB lost root language or writing direction")
        counts = Counter()
        for name, doc in docs.items():
            math = doc.xpath("//m:math", namespaces=ns)
            if any(node.get("dir") != "ltr" for node in math):
                raise ValueError(f"Lost left-to-right math markup in {name}")
            counts["mathml"] += len(math)
            counts["reflected_godel_openings"] += len(doc.xpath("//m:mtext[contains(@class,'godel-opening')]", namespaces=ns))
            for href in doc.xpath("//x:a/@href | //x:img/@src", namespaces=ns):
                parsed = urlsplit(href)
                if parsed.scheme:
                    continue
                destination = unquote(parsed.path) or name
                if "EPUB/" + destination not in filenames:
                    raise ValueError(f"Bad EPUB target {name} → {href}")
                if parsed.fragment:
                    if unquote(parsed.fragment) not in anchors[destination]:
                        raise ValueError(f"Bad EPUB anchor {name} → {href}")
                    counts["internal_fragment_links"] += 1
        if counts["mathml"] != len(source.xpath("//math")):
            raise ValueError("EPUB MathML count differs from HTML")
        counts["spine_documents"] = len(spine)
        counts["diagram_assets"] = source_figures
        return dict(counts)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("html", type=Path)
    cli.add_argument("epub", type=Path)
    cli.add_argument("--diagnostic", action="store_true")
    args = cli.parse_args()
    source_bytes = args.html.read_bytes()
    tree = html.fromstring(source_bytes, parser=html.HTMLParser(encoding="utf-8"))
    source_ids = set(tree.xpath("//@id"))
    resources, licenses, figures = publication_assets(args.html.parent, tree, args.diagnostic)
    documents = content_documents(tree)
    license_page, body = xhtml_page("فانٹاں دے لائسنس")
    add(body, XHTML, "h1", "فانٹاں دے لائسنس")
    for name, text in licenses.items():
        add(body, XHTML, "h2", name, lang="en", dir="ltr")
        add(body, XHTML, "pre", text.replace("\f", "\n"), lang="en", dir="ltr")
    for node in body:
        if node.get("lang"):
            node.set(tag(XML, "lang"), node.get("lang"))
    documents["font-licenses.xhtml"] = license_page
    nav = documents["nav.xhtml"].find(".//" + tag(XHTML, "ol"))
    add(add(nav, XHTML, "li"), XHTML, "a", "فانٹاں دے لائسنس", href="font-licenses.xhtml")
    source_hash = sha256(source_bytes).hexdigest()
    book_id = "urn:uuid:" + str(uuid5(NAMESPACE_URL, f"openlogic-pnb-Arab-PK:{SOURCE_REVISION}:{source_hash}"))
    description = tree.find("./head/meta[@name='description']").get("content")
    package = opf_package(documents, resources, book_id, "2026-11-13T00:00:00Z", description)
    container = etree.Element(tag(OCF, "container"), nsmap={None: OCF}, version="1.0")
    add(add(container, OCF, "rootfiles"), OCF, "rootfile",
        **{"full-path": "EPUB/package.opf", "media-type": "application/oebps-package+xml"})
    with ZipFile(args.epub, "w") as archive:
        zip_entry(archive, "mimetype", MIMETYPE, ZIP_STORED)
        zip_entry(archive, "META-INF/container.xml", serialize(container))
        zip_entry(archive, "EPUB/package.opf", serialize(package))
        for name, doc in documents.items():
            zip_entry(archive, "EPUB/" + name, serialize(doc))
        for name, (data, _) in resources.items():
            zip_entry(archive, "EPUB/" + name, data)
    counts = audit_archive(args.epub, tree, source_ids, figures)
    record = {
        "diagnostic": args.diagnostic,
        "html_sha256": source_hash,
        "epub_sha256": sha256(args.epub.read_bytes()).hexdigest(),
        **counts,
    }
    args.epub.with_suffix(".json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(record)


if __name__ == "__main__":
    main()
