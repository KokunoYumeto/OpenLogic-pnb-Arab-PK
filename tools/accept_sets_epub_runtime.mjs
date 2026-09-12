// Silent runtime acceptance for the actual archived Punjabi Sets EPUB.
// Reuses the accepted English pipeline's EPUB.js 0.3.93 + Chromium toolchain.
import crypto from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, "..");
const args = process.argv.slice(2);
if (args.length !== 8 || args[0] !== "--epub" || args[2] !== "--qa" || args[4] !== "--output-dir" || args[6] !== "--runtime-root") {
  throw new Error("Usage: node accept_sets_epub_runtime.mjs --epub path --qa path --output-dir path --runtime-root path");
}
const epubPath = path.resolve(args[1]);
const independentQaPath = path.resolve(args[3]);
const outputDir = path.resolve(args[5]);
const runtimeRoot = path.resolve(args[7]);
const outputPath = path.join(outputDir, "EPUB_RUNTIME_ACCEPTANCE.json");
const screenshotDir = path.join(outputDir, "runtime-screenshots");
const epubJsPath = path.join(runtimeRoot, "tools", "epub-runtime", "node_modules", "epubjs", "dist", "epub.min.js");
const jsZipPath = path.join(runtimeRoot, "tools", "epub-runtime", "node_modules", "jszip", "dist", "jszip.min.js");
const require = createRequire(import.meta.url);
const puppeteer = require(path.join(runtimeRoot, "tools", "ace", "node_modules", "puppeteer"));

function sha256(payload) {
  return crypto.createHash("sha256").update(payload).digest("hex");
}
function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}
function expect(condition, label, failures) {
  if (!condition) failures.push(label);
}

const epubBytes = fs.readFileSync(epubPath);
const qa = readJson(independentQaPath);
if (qa.status !== "pass") throw new Error("independent EPUB QA did not pass");
if (sha256(epubBytes) !== qa.artifact.sha256) throw new Error("EPUB digest drift before runtime acceptance");
fs.mkdirSync(outputDir, { recursive: true });
fs.mkdirSync(screenshotDir, { recursive: true });

const harness = `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Punjabi Sets EPUB runtime harness</title>
<style>html,body{margin:0;background:#e9e9e9}#area{width:360px;height:900px;margin:0 auto;background:white;overflow:hidden}</style></head>
<body><main><div id="area"></div></main><script src="/jszip.min.js"></script><script src="/epub.min.js"></script></body></html>`;
const serverRequests = [];
const server = http.createServer((request, response) => {
  const url = new URL(request.url || "/", "http://127.0.0.1");
  serverRequests.push({ method: request.method || "GET", path: url.pathname });
  const resources = {
    "/harness.html": { type: "text/html; charset=utf-8", body: Buffer.from(harness) },
    "/jszip.min.js": { type: "text/javascript; charset=utf-8", body: fs.readFileSync(jsZipPath) },
    "/epub.min.js": { type: "text/javascript; charset=utf-8", body: fs.readFileSync(epubJsPath) },
    "/book.epub": { type: "application/epub+zip", body: epubBytes },
    "/favicon.ico": { type: "image/x-icon", body: Buffer.alloc(0) },
  };
  const resource = resources[url.pathname];
  if (!resource) {
    response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    response.end("not found");
    return;
  }
  response.writeHead(200, {
    "Content-Type": resource.type,
    "Content-Length": resource.body.length,
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Permissions-Policy": "unload=(self)",
  });
  if (request.method === "HEAD") response.end();
  else response.end(resource.body);
});
await new Promise((resolve, reject) => {
  server.once("error", reject);
  server.listen(0, "127.0.0.1", resolve);
});
const address = server.address();
if (!address || typeof address === "string") throw new Error("failed to bind isolated localhost server");
const origin = `http://127.0.0.1:${address.port}`;

const browser = await puppeteer.launch({
  headless: true,
  executablePath: puppeteer.executablePath(),
  args: ["--disable-speech-api", "--no-sandbox"],
});
const page = await browser.newPage();
await page.setViewport({ width: 420, height: 940, deviceScaleFactor: 1 });
const externalRequests = [];
const requestFailures = [];
const pageErrors = [];
const consoleErrors = [];
await page.setRequestInterception(true);
page.on("request", (request) => {
  const url = request.url();
  if (url.startsWith(origin + "/") || url.startsWith("blob:") || url.startsWith("data:") || url === "about:blank") request.continue();
  else {
    externalRequests.push(url);
    request.abort("blockedbyclient");
  }
});
page.on("requestfailed", (request) => requestFailures.push({ url: request.url(), error: request.failure()?.errorText || "unknown" }));
page.on("pageerror", (error) => pageErrors.push(String(error)));
page.on("console", (message) => {
  if (message.type() === "error") consoleErrors.push(message.text());
});
await page.evaluateOnNewDocument(() => {
  window.__pnbSpeechCalls = [];
  Object.defineProperty(window, "speechSynthesis", {
    configurable: true,
    value: {
      getVoices: () => [],
      speak: (utterance) => window.__pnbSpeechCalls.push(String(utterance?.text || "")),
      cancel: () => {}, pause: () => {}, resume: () => {}, addEventListener: () => {}, removeEventListener: () => {},
    },
  });
});

const representatives = [
  { href: "text/cover.xhtml", name: "01-cover" },
  { href: "text/nav.xhtml", name: "02-navigation" },
  { href: "text/read.xhtml", name: "03-read-opening" },
  { href: "text/read.xhtml#sfr-set-uni-sec", name: "04-union-diagram" },
  { href: "text/read.xhtml#sfr-set-pai-sec", name: "05-pairs-math" },
  { href: "text/provenance.xhtml", name: "06-provenance" },
];

let runtime;
try {
  await page.goto(origin + "/harness.html", { waitUntil: "load", timeout: 60000 });
  runtime = await page.evaluate(async ({ representatives }) => {
    const findings = [];
    const book = ePub("/book.epub", { openAs: "epub" });
    await book.ready;
    const [navigation, metadata] = await Promise.all([book.loaded.navigation, book.loaded.metadata]);
    const spine = book.spine.spineItems;
    const countToc = (items) => items.reduce((total, item) => total + (item.href ? 1 : 0) + countToc(item.subitems || []), 0);
    const counts = {
      spine_items: spine.length,
      unique_spine_hrefs: new Set(spine.map((section) => section.href)).size,
      toc_link_items: countToc(navigation.toc || []),
      xhtml_documents_loaded: 0,
      mathml_roots: 0,
      mathml_annotations: 0,
      svg_roots: 0,
      svg_titles: 0,
      svg_descriptions: 0,
      statements: 0,
      scripts: 0,
      empty_titles: 0,
      locale_errors: 0,
      rtl_root_errors: 0,
      math_direction_errors: 0,
      rtl_math_text_errors: 0,
      empty_bodies: 0,
    };
    for (const section of spine) {
      try {
        await section.load(book.load.bind(book));
        const doc = section.document;
        const title = (doc.querySelector("title")?.textContent || "").trim();
        const maths = Array.from(doc.getElementsByTagNameNS("http://www.w3.org/1998/Math/MathML", "math"));
        const svgs = Array.from(doc.getElementsByTagNameNS("http://www.w3.org/2000/svg", "svg"));
        counts.xhtml_documents_loaded += 1;
        counts.mathml_roots += maths.length;
        counts.mathml_annotations += doc.querySelectorAll("math annotation[encoding='application/x-tex']").length;
        counts.svg_roots += svgs.length;
        counts.svg_titles += svgs.filter((node) => node.querySelector("title")?.textContent.trim()).length;
        counts.svg_descriptions += svgs.filter((node) => node.querySelector("desc")?.textContent.trim()).length;
        counts.statements += doc.querySelectorAll(".statement-heading").length;
        counts.scripts += doc.querySelectorAll("script").length;
        counts.empty_titles += title ? 0 : 1;
        counts.locale_errors += doc.documentElement.getAttribute("lang") === "pnb-Arab-PK" ? 0 : 1;
        counts.rtl_root_errors += doc.documentElement.getAttribute("dir") === "rtl" ? 0 : 1;
        counts.math_direction_errors += maths.filter((node) => node.getAttribute("dir") !== "ltr").length;
        counts.rtl_math_text_errors += Array.from(doc.getElementsByTagNameNS("http://www.w3.org/1998/Math/MathML", "mtext")).filter((node) => /[\u0600-\u06ff]/.test(node.textContent || "") && node.getAttribute("dir") !== "rtl").length;
        counts.empty_bodies += (doc.body?.textContent || "").trim() ? 0 : 1;
      } catch (error) {
        findings.push({ href: section.href, phase: "section-load", error: String(error) });
      } finally {
        section.unload();
      }
    }
    const rendition = book.renderTo("area", { width: 360, height: 900, flow: "scrolled-doc", manager: "default", allowScriptedContent: false });
    const rendered = [];
    for (const representative of representatives) {
      const row = { ...representative, failures: [] };
      try {
        await rendition.display(representative.href);
        await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        const contents = rendition.getContents();
        if (contents.length !== 1) row.failures.push("unexpected-rendered-content-count");
        const doc = contents[0]?.document;
        if (!doc) throw new Error("rendition did not expose a document");
        row.title = (doc.querySelector("title")?.textContent || "").trim();
        row.language = doc.documentElement.getAttribute("lang") || "";
        row.direction = doc.documentElement.getAttribute("dir") || "";
        row.mathml_roots = doc.getElementsByTagNameNS("http://www.w3.org/1998/Math/MathML", "math").length;
        row.svg_roots = doc.getElementsByTagNameNS("http://www.w3.org/2000/svg", "svg").length;
        row.text_characters = (doc.body?.textContent || "").trim().length;
        row.baseline_global_horizontal_overflow = doc.documentElement.scrollWidth > doc.documentElement.clientWidth + 1;
        const style = doc.createElement("style");
        style.textContent = "body,body *{line-height:1.5!important;letter-spacing:.12em!important;word-spacing:.16em!important}p{margin-block-end:2em!important}";
        doc.head.appendChild(style);
        await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        row.text_spacing_global_horizontal_overflow = doc.documentElement.scrollWidth > doc.documentElement.clientWidth + 1;
        style.textContent = "html{font-size:200%!important}";
        await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        row.two_hundred_percent_magnification_global_horizontal_overflow = doc.documentElement.scrollWidth > doc.documentElement.clientWidth + 1;
        style.remove();
        if (!row.title) row.failures.push("empty-title");
        if (row.language !== "pnb-Arab-PK") row.failures.push("locale-mismatch");
        if (row.direction !== "rtl") row.failures.push("rtl-root-missing");
        if (row.text_characters < 100) row.failures.push("insufficient-readable-content");
        if (doc.querySelectorAll("script").length) row.failures.push("scripted-content-present");
        if (row.baseline_global_horizontal_overflow) row.failures.push("360px-global-horizontal-overflow");
        if (row.text_spacing_global_horizontal_overflow) row.failures.push("text-spacing-global-horizontal-overflow");
        if (row.two_hundred_percent_magnification_global_horizontal_overflow) row.failures.push("200-percent-magnification-global-horizontal-overflow");
      } catch (error) {
        row.failures.push("render-error");
        row.error = String(error);
      }
      rendered.push(row);
    }
    rendition.destroy();
    book.destroy();
    return {
      engine: {
        name: "epub.js",
        version: "0.3.93",
        archived_epub_opened: true,
        native_mathml_element_supported: typeof MathMLElement !== "undefined" && document.createElementNS("http://www.w3.org/1998/Math/MathML", "math") instanceof MathMLElement,
      },
      metadata: { title: metadata.title, language: metadata.language, layout: metadata.layout, identifier: metadata.identifier, direction: metadata.direction },
      counts,
      section_findings: findings,
      representative_renders: rendered,
      speech_calls: window.__pnbSpeechCalls.length,
    };
  }, { representatives });

  for (const representative of representatives) {
    await page.evaluate(async (href) => {
      // The first rendition remains in #area during the evaluation call only;
      // create a short-lived visual rendition for the screenshot.
      const area = document.getElementById("area");
      area.innerHTML = "";
      const book = ePub("/book.epub", { openAs: "epub" });
      await book.ready;
      const rendition = book.renderTo(area, { width: 360, height: 900, flow: "scrolled-doc", manager: "default", allowScriptedContent: false });
      window.__visualBook = book;
      window.__visualRendition = rendition;
      await rendition.display(href);
      await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    }, representative.href);
    await page.screenshot({ path: path.join(screenshotDir, representative.name + ".png"), fullPage: false });
    await page.evaluate(() => {
      window.__visualRendition?.destroy();
      window.__visualBook?.destroy();
      window.__visualRendition = null;
      window.__visualBook = null;
    });
  }
} finally {
  await page.close();
  await browser.close();
  await new Promise((resolve) => server.close(resolve));
}

const failures = [];
expect(runtime.engine.archived_epub_opened, "archived-epub-not-opened", failures);
expect(runtime.engine.native_mathml_element_supported, "browser-does-not-expose-native-mathml-elements", failures);
expect(runtime.metadata.language === "pnb-Arab-PK", "metadata-language-mismatch", failures);
expect(runtime.metadata.layout === "reflowable", "metadata-layout-mismatch", failures);
expect(runtime.counts.spine_items === 5, "spine-count-mismatch", failures);
expect(runtime.counts.unique_spine_hrefs === 5, "spine-hrefs-not-unique", failures);
expect(runtime.counts.toc_link_items === 10, "toc-link-count-mismatch", failures);
expect(runtime.counts.xhtml_documents_loaded === 5, "spine-document-load-count-mismatch", failures);
expect(runtime.counts.mathml_roots === 329, "mathml-count-mismatch", failures);
expect(runtime.counts.mathml_annotations === 329, "mathml-annotation-count-mismatch", failures);
expect(runtime.counts.svg_roots === 3 && runtime.counts.svg_titles === 3 && runtime.counts.svg_descriptions === 3, "svg-alternative-count-mismatch", failures);
expect(runtime.counts.statements === 39, "statement-count-mismatch", failures);
expect(runtime.counts.scripts === 0, "scripts-present-in-publication", failures);
expect(runtime.counts.empty_titles === 0 && runtime.counts.empty_bodies === 0, "empty-document", failures);
expect(runtime.counts.locale_errors === 0 && runtime.counts.rtl_root_errors === 0, "document-locale-or-direction-mismatch", failures);
expect(runtime.counts.math_direction_errors === 0, "math-direction-mismatch", failures);
expect(runtime.counts.rtl_math_text_errors === 0, "rtl-math-text-direction-mismatch", failures);
expect(runtime.section_findings.length === 0, "spine-section-load-failure", failures);
expect(runtime.representative_renders.length === representatives.length, "representative-count-mismatch", failures);
expect(runtime.representative_renders.every((row) => row.failures.length === 0), "representative-render-failure", failures);
expect(runtime.speech_calls === 0, "unexpected-speech-call", failures);
expect(externalRequests.length === 0, "external-network-request-attempted", failures);
expect(requestFailures.length === 0, "request-failure-observed", failures);
expect(pageErrors.length === 0, "page-error-observed", failures);
const classifiedConsole = consoleErrors.filter((message) => message === "Permissions policy violation: unload is not allowed in this document.");
const actionableConsole = consoleErrors.filter((message) => !classifiedConsole.includes(message));
expect(actionableConsole.length === 0, "actionable-console-error", failures);

const screenshots = fs.readdirSync(screenshotDir).filter((name) => name.endsWith(".png")).sort().map((name) => {
  const payload = fs.readFileSync(path.join(screenshotDir, name));
  return { file: name, bytes: payload.length, sha256: sha256(payload) };
});
expect(screenshots.length === representatives.length, "screenshot-count-mismatch", failures);

const report = {
  schema: "pnb-sets-epub-runtime-acceptance/1",
  status: failures.length ? "fail" : "pass",
  input: { epub: epubPath, epub_bytes: epubBytes.length, epub_sha256: sha256(epubBytes), independent_qa_sha256: sha256(fs.readFileSync(independentQaPath)) },
  execution: {
    reading_engine: "EPUB.js 0.3.93 in headless Chromium",
    actual_archived_epub: true,
    viewport_css_pixels: { width: 360, height: 900 },
    external_network_denied: true,
    transport: "ephemeral loopback-only HTTP server; all non-loopback requests aborted",
    speech_synthesis_stubbed_and_silent: true,
    scripted_content_allowed: false,
    magnification_probe: "200% root font size at 360 CSS pixels",
    text_spacing_probe: "1.5 line height, 0.12em letter spacing, 0.16em word spacing at 360 CSS pixels",
    scope: "All five archived spine documents loaded; six representative locations rendered and captured. This is bounded runtime evidence, not an all-device or human accessibility certification.",
  },
  runtime,
  network: { loopback_requests: serverRequests, external_request_attempts: externalRequests, request_failures: requestFailures },
  browser_errors: { page: pageErrors, actionable_console: actionableConsole, classified_engine_or_browser_warnings: classifiedConsole },
  screenshots,
  failures,
  runner_sha256: sha256(fs.readFileSync(fileURLToPath(import.meta.url))),
};
fs.writeFileSync(outputPath, JSON.stringify(report, null, 2) + "\n", "utf8");
process.stdout.write(JSON.stringify({ status: report.status, spine_documents_loaded: runtime.counts.xhtml_documents_loaded, mathml_roots: runtime.counts.mathml_roots, representative_renders: runtime.representative_renders.length, screenshots: screenshots.length, external_request_attempts: externalRequests.length, failures, report: { path: outputPath, bytes: fs.statSync(outputPath).size, sha256: sha256(fs.readFileSync(outputPath)) } }, null, 2) + "\n");
if (failures.length) process.exitCode = 1;
