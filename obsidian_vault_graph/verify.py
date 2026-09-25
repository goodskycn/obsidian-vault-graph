# -*- coding: utf-8 -*-
"""校验：frontmatter 覆盖率、链接解析、标签统计"""
import collections
import os
import re

from . import util


def verify(vault):
    """返回校验结果 dict"""
    files = []
    for dirpath, dirnames, filenames in os.walk(vault):
        dirnames[:] = [d for d in dirnames if d not in util.SKIP_DIRS]
        for fn in filenames:
            if fn.lower().endswith(".md"):
                rel = os.path.relpath(os.path.join(dirpath, fn), vault).replace("\\", "/")
                files.append(rel)

    paths = set(f[:-3] for f in files)
    basenames = collections.defaultdict(list)
    for p in paths:
        basenames[p.split("/")[-1]].append(p)

    link_re = re.compile(r"\[\[([^\[\]]+?)\]\]")
    fm_count = related_count = total_links = 0
    unresolved = []
    tag_count = collections.Counter()

    for rel in files:
        try:
            txt = open(os.path.join(vault, rel), encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        if txt.startswith("---"):
            fm_count += 1
            blk = txt.split("---")[1]
            for line in blk.splitlines():
                line = line.strip()
                if line.startswith("- "):
                    tag_count[util.tag_clean(line[2:].strip())] += 1
        if util.MARKER in txt:
            related_count += 1
        for m in link_re.finditer(txt):
            target = m.group(1).split("|")[0].strip()
            total_links += 1
            if target in paths or target in basenames:
                continue
            unresolved.append("%s -> %s" % (rel, target))

    moc_files = [f for f in files if f.split("/")[-1].startswith("_MOC ")]
    return {
        "md_files": len(files),
        "with_frontmatter": fm_count,
        "with_related_section": related_count,
        "wikilinks_total": total_links,
        "unresolved": unresolved,
        "moc_files": moc_files,
        "distinct_tags": len(tag_count),
        "top_tags": tag_count.most_common(30),
    }


def format_report(res):
    lines = []
    lines.append("md 文件          %d" % res["md_files"])
    lines.append("带 frontmatter   %d" % res["with_frontmatter"])
    lines.append("带相关笔记区块   %d" % res["with_related_section"])
    lines.append("双链总数         %d" % res["wikilinks_total"])
    lines.append("未解析链接       %d" % len(res["unresolved"]))
    lines.append("MOC 枢纽笔记     %d" % len(res["moc_files"]))
    lines.append("标签种类         %d" % res["distinct_tags"])
    if res["unresolved"]:
        lines.append("")
        lines.append("--- 未解析链接（前 20）---")
        lines.extend(res["unresolved"][:20])
    lines.append("")
    lines.append("--- 标签 top 15 ---")
    lines.extend("%-30s %d" % (t, c) for t, c in res["top_tags"][:15])
    return "\n".join(lines)
