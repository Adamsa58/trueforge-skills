#!/usr/bin/env python3
"""Extract LLM leaderboard data from saved web_fetch_exa output.

Reads the markdown that web_fetch_exa returned (TrueForge saves large tool
results under /opt/tf/tool-results), pulls every markdown table and every
"model card" block out of it, and merges rows that describe the same model.

Writes /opt/tf/work/tables.json (every table as found) and
/opt/tf/work/models.json (one merged record per model). No numbers are
typed by the agent: everything comes straight from the fetched text.

Usage: python3 extract.py [input_file] [output_dir]
"""
import glob
import json
import os
import re
import sys

DEFAULT_INPUT_GLOB = "/opt/tf/tool-results/*"
DEFAULT_OUT_DIR = "/opt/tf/work"

# Header text (lowercase) -> merged field name. Anything numeric that is not
# listed here (and not skipped) becomes a per-source metric.
FIELD_HEADERS = {
    "model": "name", "model name": "name", "name": "name",
    "creator": "creator", "model creator": "creator", "provider": "creator",
    "organization": "creator", "lab": "creator",
    "parameters": "params", "size": "params", "params": "params",
    "context": "context", "context window": "context", "context length": "context",
    "license": "license",
    "type": "openness",
    "price": "price", "api price / 1m": "price", "input / output": "price",
    "input cost (1m)": "input_price", "output cost (1m)": "output_price",
    "output speed tokens/s": "speed", "throughput": "speed", "speed": "speed",
    "latency": "latency", "knowledge cutoff": "knowledge_cutoff",
}
SKIP_HEADERS = {"rank", "#", "evidence", "conditional range", "weights",
                "providers", "provider benchmarks", ""}
CARD_LABELS = {"parameters": "params", "context": "context",
               "input / output": "price", "license": "license"}

SEP_CELL = re.compile(r"^:?-{3,}:?$")
NUMERIC = re.compile(r"^[\s$~<>]*-?\d[\d,]*(\.\d+)?")


def newest_input():
    files = [f for f in glob.glob(DEFAULT_INPUT_GLOB) if os.path.isfile(f)]
    if not files:
        sys.exit("No saved tool results found in /opt/tf/tool-results. "
                 "Run the web_fetch_exa step first (with maxCharacters 60000).")
    return max(files, key=os.path.getmtime)


def cells(line):
    parts = line.strip().strip("|").split("|")
    return [p.strip() for p in parts]


def is_row(line):
    s = line.strip()
    return s.startswith("|") and s.count("|") >= 2


def is_sep(line):
    c = cells(line)
    return bool(c) and all(SEP_CELL.match(x) for x in c if x)


def split_sections(text):
    """Split into [(title, url, lines)] using the 'URL: ' lines Exa emits."""
    lines = text.splitlines()
    sections, cur = [], None
    for i, line in enumerate(lines):
        m = re.match(r"^URL:\s*(\S+)", line)
        if m:
            title = ""
            for back in range(i - 1, max(i - 4, -1), -1):
                if lines[back].startswith("#"):
                    title = lines[back].lstrip("#").strip()
                    break
            cur = {"title": title, "url": m.group(1), "lines": []}
            sections.append(cur)
        elif cur is not None:
            cur["lines"].append(line)
    if not sections:
        sections.append({"title": "input", "url": "", "lines": lines})
    return sections


def site_name(url):
    m = re.match(r"https?://(www\.)?([^/]+)", url or "")
    return m.group(2) if m else "source"


def next_nonblank(lines, i):
    j = i + 1
    while j < len(lines) and not lines[j].strip():
        j += 1
    return j


def parse_tables(lines):
    tables, heading, i = [], "", 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
        j = next_nonblank(lines, i)
        if is_row(line) and not is_sep(line) and j < len(lines) and is_sep(lines[j]):
            header = cells(line)
            rows, k = [], next_nonblank(lines, j)
            while k < len(lines) and is_row(lines[k]):
                if not is_sep(lines[k]):
                    c = cells(lines[k])
                    if len(c) >= len(header) - 1:
                        c = (c + [""] * len(header))[:len(header)]
                        rows.append(dict(zip(header, c)))
                k = next_nonblank(lines, k)
            if rows:
                tables.append({"heading": heading, "columns": header, "rows": rows})
            i = k
            continue
        i += 1
    return tables


def parse_cards(lines):
    """'### name' followed by label/value pairs (e.g. Seminal AI)."""
    rows, i = [], 0
    while i < len(lines):
        if lines[i].startswith("### "):
            name = lines[i][4:].strip()
            rec, k = {"Model": name}, i + 1
            while k < len(lines) and not lines[k].startswith("#"):
                label = lines[k].strip().lower()
                if label in CARD_LABELS:
                    v = next_nonblank(lines, k)
                    if v < len(lines):
                        rec[lines[k].strip()] = lines[v].strip()
                        k = v
                k += 1
            if len(rec) >= 3:
                rows.append(rec)
            i = k
            continue
        i += 1
    if not rows:
        return []
    cols = ["Model"] + [c for c in ["Parameters", "Context", "Input / output", "License"]
                        if any(c in r for r in rows)]
    return [{"heading": "Model cards", "columns": cols,
             "rows": [{c: r.get(c, "") for c in cols} for r in rows]}]


def norm_key(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())


def split_name(raw):
    """'GLM-5.3 Flash · Zhipu AI' -> ('GLM-5.3 Flash', 'Zhipu AI')."""
    for sep in (" · ", " · ", " - by "):
        if sep in raw:
            a, b = raw.split(sep, 1)
            return a.strip(), b.strip()
    return raw.strip(), ""


def first_number(value):
    m = NUMERIC.match(value or "")
    if not m:
        return None
    try:
        return float(re.sub(r"[^\d.\-]", "", m.group(0)))
    except ValueError:
        return None


def merge(sources):
    models = {}
    for src in sources:
        site = site_name(src["url"])
        for t in src["tables"]:
            name_col = next((c for c in t["columns"] if FIELD_HEADERS.get(c.lower()) == "name"), None)
            if name_col is None:
                continue
            for row in t["rows"]:
                name, creator = split_name(row.get(name_col, ""))
                if not name or name.startswith("-"):
                    continue
                key = norm_key(name)
                if not key:
                    continue
                m = models.setdefault(key, {"name": name, "key": key, "metrics": {}, "sources": []})
                if site not in m["sources"]:
                    m["sources"].append(site)
                if creator and not m.get("creator"):
                    m["creator"] = creator
                for col, val in row.items():
                    h = col.lower().strip()
                    if col == name_col or h in SKIP_HEADERS or not val or val in ("-", "—"):
                        continue
                    field = FIELD_HEADERS.get(h)
                    if field and field != "name":
                        m.setdefault(field, val)
                    elif first_number(val) is not None:
                        # A bare "score" column only makes sense with its section title
                        # (e.g. "Best in Reasoning (GPQA Diamond)"); other headers stand alone.
                        label = t["heading"] + " " + h if h == "score" and t["heading"] \
                            and t["heading"].lower() not in ("rankings", "model cards") else h
                        m["metrics"]["%s: %s" % (site, label)] = val
    return sorted(models.values(), key=lambda m: m["name"].lower())


def main():
    src_path = sys.argv[1] if len(sys.argv) > 1 else newest_input()
    out_dir = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    with open(src_path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    # Saved tool results may be the raw MCP JSON; unwrap its text parts.
    if text.lstrip().startswith(("{", "[")):
        try:
            data = json.loads(text)
            parts = data.get("content", data) if isinstance(data, dict) else data
            text = "\n".join(p.get("text", "") for p in parts if isinstance(p, dict)) or text
        except (ValueError, AttributeError):
            pass

    sources = []
    for sec in split_sections(text):
        tables = parse_tables(sec["lines"]) + parse_cards(sec["lines"])
        sources.append({"title": sec["title"], "url": sec["url"], "tables": tables})
    models = merge(sources)

    with open(os.path.join(out_dir, "tables.json"), "w", encoding="utf-8") as f:
        json.dump(sources, f, ensure_ascii=False, indent=1)
    with open(os.path.join(out_dir, "models.json"), "w", encoding="utf-8") as f:
        json.dump(models, f, ensure_ascii=False, indent=1)

    print("input:", src_path)
    for s in sources:
        print("  %s: %d tables, %d rows" % (site_name(s["url"]), len(s["tables"]),
                                             sum(len(t["rows"]) for t in s["tables"])))
    print("models merged:", len(models))
    print("wrote", os.path.join(out_dir, "models.json"), "and tables.json")


if __name__ == "__main__":
    main()
