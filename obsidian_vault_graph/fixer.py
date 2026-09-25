# -*- coding: utf-8 -*-
"""历史遗留修复：指向已删 PDF 的双链、文件名首尾空格"""
import os
import re

from . import util


def fix_filename_spaces(vault):
    """清理文件名首尾空格，返回 [(旧名, 新名)]"""
    renamed = []
    for dirpath, dirnames, filenames in os.walk(vault):
        dirnames[:] = [d for d in dirnames if d not in util.SKIP_DIRS]
        for fn in filenames:
            if not fn.lower().endswith(".md"):
                continue
            stem, ext = os.path.splitext(fn)
            fixed = stem.strip()
            if fixed != stem and fixed:
                src = os.path.join(dirpath, fn)
                dst = os.path.join(dirpath, fixed + ext)
                if os.path.exists(dst):
                    continue
                os.rename(src, dst)
                renamed.append((fn, fixed + ext))
    return renamed


def fix_pdf_links(vault):
    """把 [[xxx.note.pdf]] 之类指向 PDF 的双链改为指向同名 md，返回 (条数, 文件列表)"""
    fixed_links = 0
    files_fixed = []
    for rel, p, top, subdir, name in util.list_notes(vault):
        try:
            txt = open(p, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        if ".pdf" not in txt:
            continue
        new = re.sub(r"\[\[([^\[\]\|]+?)\.pdf(\|[^\[\]]*)?\]\]",
                     lambda m: "[[%s%s]]" % (m.group(1), m.group(2) or ""), txt)
        if new != txt:
            n = len(re.findall(r"\[\[[^\[\]\|]+?\.pdf(\|[^\[\]]*)?\]\]", txt))
            fixed_links += n
            files_fixed.append(rel)
            ok, err = util.write_resilient(p, new)
            if not ok:
                raise IOError(err)
    return fixed_links, files_fixed
