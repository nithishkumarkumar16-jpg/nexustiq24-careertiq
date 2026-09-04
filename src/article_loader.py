"""Loads local Markdown support articles; no hosted knowledge source is used."""
import re
from pathlib import Path
from typing import Any
from src.config import KB_DIR


def _parse_value(value: str):
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        return [x.strip() for x in value[1:-1].split(",") if x.strip()]
    return value


def load_articles() -> list[dict[str, Any]]:
    articles=[]
    for path in sorted(KB_DIR.glob("*.md")):
        raw=path.read_text(encoding="utf-8")
        match=re.match(r"^---\n(.*?)\n---\n(.*)$",raw,re.S)
        if not match: continue
        meta={}
        for line in match.group(1).splitlines():
            if ":" in line:
                key,value=line.split(":",1);meta[key.strip()]=_parse_value(value)
        sections=[]; current="Overview"; buffer=[]
        for line in match.group(2).strip().splitlines():
            if line.startswith("# "):
                if buffer: sections.append({"heading":current,"text":"\n".join(buffer).strip()})
                current=line[2:].strip();buffer=[]
            else: buffer.append(line)
        if buffer: sections.append({"heading":current,"text":"\n".join(buffer).strip()})
        meta["chunks"]=[{"article_id":meta["id"],"title":meta["title"],"section":section["heading"],"source_text":section["text"]} for section in sections if section["text"]]
        meta["sections"]=sections; meta["path"]=str(path); articles.append(meta)
    return articles
