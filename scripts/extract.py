#!/usr/bin/env python3
"""Build a provenance-preserving Lord of the Mysteries chronology dataset."""
from __future__ import annotations
import csv, hashlib, json, re, sys, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "sources"
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"
LOG_DIR = ROOT / "logs"
HEADERS = {"User-Agent": "lotm-chronology-extractor/1.0 (research dataset; contact via repository)"}
FANDOM_API = "https://lordofthemysteries.fandom.com/api.php"
FANDOM_ROOT = "https://lordofthemysteries.fandom.com"
NOVEL_ROOT = "https://www.novelwiki.net/lord-of-the-mysteries/"

TEMPLATES = [
    ("pre-epoch", "Pre-Epoch", "Template:Timeline/Pre-Epoch"),
    ("first-epoch", "First Epoch: The Age of Chaos", "Template:Timeline/First Epoch"),
    ("second-epoch", "Second Epoch: The Dark Epoch", "Template:Timeline/Second Epoch"),
    ("third-epoch", "Third Epoch: The Cataclysm Epoch", "Template:Timeline/Third Epoch"),
    ("fourth-epoch", "Fourth Epoch: The Epoch of the Gods", "Template:Timeline/Fourth Epoch"),
    ("fifth-epoch", "Fifth Epoch: The Iron Age", "Template:Timeline/Fifth Epoch"),
    ("fifth-epoch-2", "Fifth Epoch: Starting Point of Circle of Inevitability", "Template:Timeline/Fifth Epoch 2"),
]

session = requests.Session()
session.headers.update(HEADERS)


def fetch(url, **params):
    r = session.get(url, params=params or None, timeout=45)
    r.raise_for_status()
    return r


def clean_wikitext(text: str) -> str:
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.S)
    text = re.sub(r"<ref[^>]*/>", "", text)
    text = re.sub(r"\{\{[^{}]*\}\}", "", text)
    text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\[https?://[^ ]+ ([^\]]+)\]", r"\1", text)
    text = re.sub(r"'''|''|<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_timeline_table(wikitext: str, section_id: str, section_title: str):
    records = []
    current_label = None
    for block in re.split(r"\n\|-", wikitext):
        lines = [x.rstrip() for x in block.splitlines()]
        cells = []
        current = None
        citations = []
        for book, chapter in re.findall(r"Cite Book\|([^|}]+)\|([^|}]+)", block):
            citation = {"book": book.strip(), "chapter": chapter.strip()}
            if citation not in citations:
                citations.append(citation)
        for line in lines:
            if line.startswith("|}") or line.startswith("<noinclude") or line.startswith("</noinclude"):
                continue
            if line.startswith("!") or line.startswith("|"):
                if line.startswith("|-") or line.startswith("!-"):
                    continue
                if current is not None:
                    cells.append(current)
                marker = line[0]
                value = line[1:].strip()
                if value.startswith("colspan") and "|" in value:
                    value = value.split("|", 1)[1]
                current = [marker, value]
            elif current is not None:
                current[1] += "\n" + line
        if current is not None:
            cells.append(current)
        cells = [(marker, clean_wikitext(value)) for marker, value in cells]
        if not cells or any(v.lower() in {"time", "date", "event"} for _, v in cells):
            continue
        if len(cells) == 1 and cells[0][0] == "!":
            current_label = cells[0][1]
            continue
        vals = [v for _, v in cells]
        if not any(vals):
            continue
        if len(vals) >= 3:
            time_label, date_label, event = vals[0], vals[1], " ".join(x for x in vals[2:] if x)
        elif len(vals) == 2:
            time_label, date_label, event = vals[0], "", vals[1]
        else:
            time_label, date_label, event = "", "", vals[0]
        if event and event not in {"Event", "Time"}:
            rid = hashlib.sha1(f"{section_id}|{current_label}|{time_label}|{date_label}|{event}".encode()).hexdigest()[:12]
            records.append({
                "id": f"tl-{rid}", "section": section_title, "section_id": section_id,
                "era_label": current_label, "time": time_label, "date": date_label,
                "event": event, "novel_citations": citations,
                "source_template": f"{FANDOM_ROOT}/wiki/{section_id}",
                "source_page": "https://lordofthemysteries.fandom.com/wiki/Timeline",
            })
    return records


def html_to_markdown(html: str) -> str:
    try:
        from markdownify import markdownify as md
        return md(html, heading_style="ATX", bullets="-").strip() + "\n"
    except Exception:
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text("\n", strip=True) + "\n"


def page_main_html(url: str):
    r = fetch(url)
    soup = BeautifulSoup(r.text, "html.parser")
    main = soup.select_one("main") or soup
    for x in main.select("nav, footer, script, style, form, .sidebar, .comments"):
        x.decompose()
    return r.text, str(main), soup.title.get_text(" ", strip=True) if soup.title else ""


def novel_index(kind: str):
    url = urljoin(NOVEL_ROOT, kind)
    html, main, _ = page_main_html(url)
    soup = BeautifulSoup(main, "html.parser")
    items = []
    for a in soup.select("a[href]"):
        href = urljoin(url, a["href"])
        text = a.get_text(" ", strip=True)
        if kind == "summaries" and "/summaries/chapters-" in href and href.rstrip("/") != url.rstrip("/"):
            m = re.search(r"Chapters? ([\d,]+)[–-]([\d,]+)", text)
            if m:
                items.append({"title": text, "url": href, "start": int(m.group(1).replace(",", "")), "end": int(m.group(2).replace(",", ""))})
        if kind == "story-arcs/" and "summaries/chapters-" in href:
            m = re.search(r"^(.*?)\s+Chapters? ([\d,]+)[–-]([\d,]+)\s*(.*)$", text)
            if m:
                items.append({"title": m.group(1).strip(), "url": href, "start": int(m.group(2).replace(",", "")), "end": int(m.group(3).replace(",", "")), "description": m.group(4).strip()})
    # de-duplicate while retaining order
    seen, out = set(), []
    for x in items:
        key = (x["title"], x["url"], x["start"], x["end"])
        if key not in seen:
            seen.add(key); out.append(x)
    return url, html, out


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    started = datetime.now(timezone.utc).isoformat()
    counts = {}
    # Fandom source and expanded templates
    main_json = fetch(FANDOM_API, action="parse", page="Timeline", prop="wikitext", format="json").json()
    (SOURCE_DIR / "fandom" ).mkdir(parents=True, exist_ok=True)
    (SOURCE_DIR / "fandom" / "Timeline.wikitext").write_text(main_json["parse"]["wikitext"]["*"] + "\n", encoding="utf-8")
    timeline = []
    for sid, title, page in TEMPLATES:
        d = fetch(FANDOM_API, action="parse", page=page, prop="wikitext", format="json").json()
        w = d["parse"]["wikitext"]["*"]
        (SOURCE_DIR / "fandom" / f"{sid}.wikitext").write_text(w + "\n", encoding="utf-8")
        timeline.extend(parse_timeline_table(w, page.replace("Template:", ""), title))
        time.sleep(0.15)
    write_json(DATA_DIR / "timeline.json", {"source": "https://lordofthemysteries.fandom.com/wiki/Timeline", "records": timeline})
    with (DATA_DIR / "timeline.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["id", "section", "section_id", "era_label", "time", "date", "event", "novel_citations", "source_template", "source_page"]
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(timeline)
    counts["timeline_records"] = len(timeline)

    # Novel Wiki summaries
    sum_index_url, sum_index_html, summaries = novel_index("summaries")
    (SOURCE_DIR / "novelwiki" / "summaries-index.html").write_text(sum_index_html, encoding="utf-8")
    write_json(DATA_DIR / "summaries.json", {"source": sum_index_url, "items": summaries})
    for i, item in enumerate(summaries, 1):
        html, main, title = page_main_html(item["url"])
        slug = re.sub(r"[^a-z0-9]+", "-", item["url"].rstrip("/").split("/")[-1].lower()).strip("-")
        (SOURCE_DIR / "novelwiki" / f"summary-{slug}.html").write_text(html, encoding="utf-8")
        text = html_to_markdown(main)
        doc = f"# {item['title']}\n\n- Source: [{item['url']}]({item['url']})\n- Chapter range: {item['start']}–{item['end']}\n- Extracted: {datetime.now(timezone.utc).isoformat()}\n\n{text}"
        (DATA_DIR / "summaries" / f"{i:02d}-{slug}.md").write_text(doc, encoding="utf-8")
        time.sleep(0.15)
    counts["summary_pages"] = len(summaries)

    # Story arcs: index metadata plus dedicated local pages, linked to the source chapter summaries.
    arc_index_url, arc_index_html, arcs = novel_index("story-arcs/")
    (SOURCE_DIR / "novelwiki" / "story-arcs-index.html").write_text(arc_index_html, encoding="utf-8")
    write_json(DATA_DIR / "arcs.json", {"source": arc_index_url, "items": arcs})
    for i, arc in enumerate(arcs, 1):
        slug = re.sub(r"[^a-z0-9]+", "-", arc["title"].lower()).strip("-")
        doc = (f"# {arc['title']}\n\n- Chapters: {arc['start']}–{arc['end']}\n"
               f"- Chapter-summary source: [{arc['url']}]({arc['url']})\n"
               f"- Story-arc index: [{arc_index_url}]({arc_index_url})\n\n{arc.get('description','')}\n")
        (DATA_DIR / "arcs" / f"{i:02d}-{slug}.md").write_text(doc, encoding="utf-8")
    counts["story_arcs"] = len(arcs)

    # A machine-readable crosswalk between chapter ranges and arcs.
    crosswalk = []
    for s in summaries:
        matches = [a["title"] for a in arcs if not (a["end"] < s["start"] or a["start"] > s["end"])]
        crosswalk.append({"summary": s["title"], "start": s["start"], "end": s["end"], "arcs": matches, "summary_url": s["url"]})
    write_json(DATA_DIR / "chapter-crosswalk.json", {"items": crosswalk})

    finished = datetime.now(timezone.utc).isoformat()
    log = {"started_at": started, "finished_at": finished, "status": "success", "counts": counts, "sources": [
        "https://lordofthemysteries.fandom.com/wiki/Timeline",
        "https://www.novelwiki.net/lord-of-the-mysteries/summaries",
        "https://www.novelwiki.net/lord-of-the-mysteries/story-arcs/",
    ]}
    LOG_DIR.mkdir(exist_ok=True)
    (LOG_DIR / f"run-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json").write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    (LOG_DIR / "latest.json").write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(log, indent=2))

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        LOG_DIR.mkdir(exist_ok=True)
        failure = {"finished_at": datetime.now(timezone.utc).isoformat(), "status": "failed", "error": repr(exc)}
        (LOG_DIR / "latest.json").write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
        raise
