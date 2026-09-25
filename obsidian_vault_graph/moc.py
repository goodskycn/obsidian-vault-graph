# -*- coding: utf-8 -*-
"""MOC 枢纽笔记：库总览 + 各主题文件夹索引 + 标签索引"""
import collections
import datetime
import os

from . import util


def tag_counter_from_notes(notes, notes_tags):
    """从已计算好的标签字典统计 {tag: count}"""
    counter = collections.Counter()
    for rel, p, top, subdir, name in notes:
        for t in notes_tags[rel]:
            counter[t] += 1
    return counter


def generate_mocs(vault, notes, write=True):
    """生成各主题文件夹的 _MOC <主题>.md，返回生成的文件路径列表"""
    today = datetime.date.today().isoformat()
    by_top = collections.defaultdict(list)
    for rel, p, top, subdir, name in notes:
        by_top[top].append((subdir, name, rel))

    made = []
    for top, items in sorted(by_top.items(), key=lambda x: -len(x[1])):
        if top == "未分类":
            continue
        items.sort(key=lambda x: (x[0], x[1]))
        lines = ["---", "tags:", "  - MOC", "  - %s" % util.tag_clean(top), "---", "",
                 "# 📚 %s" % top, "",
                 "%s · 共 %d 篇 · %s" % (util.GEN_NOTE, len(items), today), "",
                 "← 返回 [[🏠 知识库总览]]", ""]
        cur = None
        for subdir, name, rel in items:
            label = "（本目录）" if (not subdir or subdir == top) else subdir.split("/")[-1]
            if label != cur:
                if cur is not None:
                    lines.append("")
                lines.append("## %s" % label)
                cur = label
            lines.append("- %s" % util.safe_link(rel, util.pretty(name)))
        if write:
            out = os.path.join(vault, top, "_MOC %s.md" % top)
            ok, err = util.write_resilient(out, "\n".join(lines) + "\n")
            if not ok:
                raise IOError("写入失败: %s (%s)" % (out, err))
        made.append("%s/_MOC %s.md" % (top, top))
    return made


def generate_overview(vault, notes, write=True):
    """生成库根目录的 🏠 知识库总览.md"""
    today = datetime.date.today().isoformat()
    by_top = collections.defaultdict(list)
    for rel, p, top, subdir, name in notes:
        by_top[top].append((subdir, name, rel))

    lines = ["---", "tags:", "  - MOC", "  - 总览", "---", "",
             "# 🏠 知识库总览", "", "%s · %s" % (util.GEN_NOTE, today), "",
             "共 %d 篇笔记 · %d 个主题板块" % (len(notes), len([k for k in by_top if k != "未分类"])),
             "", "## 🗂 主题板块", ""]
    for top, items in sorted(by_top.items(), key=lambda x: -len(x[1])):
        if top == "未分类":
            continue
        lines.append("- [[%s/_MOC %s|%s]] · %d 篇" % (top, top, top, len(items)))
    if "未分类" in by_top:
        lines += ["", "## 📄 库根目录散篇", ""]
        for subdir, name, rel in sorted(by_top["未分类"], key=lambda x: x[1]):
            lines.append("- %s" % util.safe_link(rel, util.pretty(name)))
    lines += ["", "## 🏷 快速入口", "- [[🏷 标签索引]]", ""]
    if write:
        ok, err = util.write_resilient(os.path.join(vault, "🏠 知识库总览.md"), "\n".join(lines) + "\n")
        if not ok:
            raise IOError(err)
    return lines


def generate_tag_index(vault, notes, write=True):
    """生成 🏷 标签索引.md（直接读取各笔记 frontmatter）"""
    today = datetime.date.today().isoformat()
    tag_counter = collections.Counter()
    for rel, p, top, subdir, name in notes:
        try:
            txt = open(p, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        if txt.startswith("---"):
            blk = txt.split("---")[1]
            for line in blk.splitlines():
                line = line.strip()
                if line.startswith("- "):
                    tag_counter[util.tag_clean(line[2:].strip())] += 1

    lines = ["---", "tags:", "  - MOC", "  - 标签索引", "---", "",
             "# 🏷 标签索引", "", "%s · %s" % (util.GEN_NOTE, today), "",
             "← 返回 [[🏠 知识库总览]]", "", "## 主题 / 内容标签", ""]
    for t, c in sorted([(k, v) for k, v in tag_counter.items() if "/" not in k], key=lambda x: -x[1]):
        lines.append("- #%s · %d 篇" % (t, c))
    lines += ["", "## 子主题标签", ""]
    for t, c in sorted([(k, v) for k, v in tag_counter.items() if "/" in k], key=lambda x: -x[1]):
        lines.append("- #%s · %d 篇" % (t, c))
    if write:
        ok, err = util.write_resilient(os.path.join(vault, "🏷 标签索引.md"), "\n".join(lines) + "\n")
        if not ok:
            raise IOError(err)
    return tag_counter
