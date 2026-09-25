# -*- coding: utf-8 -*-
"""主流程：build 一键建图（备份 → 标签 → 相关双链 → MOC → 视图配置）"""
import datetime
import os
import sys
import zipfile

from . import util, analysis, moc as moc_mod, graphview, fixer
from .verify import verify, format_report


def backup_md(vault, backup_dir=None):
    """把库内全部 md 打包成 zip，返回 (zip路径, 文件数)"""
    vault = os.path.abspath(vault)
    date = datetime.date.today().strftime("%Y%m%d")
    name = "md_backup_before_graph_%s.zip" % date
    zip_path = os.path.join(backup_dir or os.path.dirname(vault), name)
    count = 0
    with zipfile.ZipFile(util.long_path(zip_path), "w", zipfile.ZIP_DEFLATED, allowZip64=True) as z:
        for dirpath, dirnames, filenames in os.walk(vault):
            dirnames[:] = [d for d in dirnames if d not in util.SKIP_DIRS]
            for fn in filenames:
                if fn.lower().endswith(".md"):
                    p = os.path.join(dirpath, fn)
                    z.write(util.long_path(p), os.path.relpath(p, vault))
                    count += 1
    return zip_path, count


def build(vault, dry_run=False, no_backup=False, backup_dir=None,
          vocab_size=90, min_doc_freq=8, top_tags=3,
          min_sim=0.28, max_related=3,
          do_tags=True, do_related=True, do_moc=True, do_graph=True, graph_force=False,
          log=print):
    """一键建图。返回统计 dict。"""
    vault = os.path.abspath(vault)
    if not os.path.isdir(vault):
        raise NotADirectoryError("库目录不存在: %s" % vault)

    notes = util.list_notes(vault)
    if not notes:
        raise RuntimeError("库中没有找到任何 md 笔记")
    log("发现笔记 %d 篇" % len(notes))

    stats = {"notes": len(notes)}

    if not no_backup:
        if dry_run:
            log("[dry-run] 将跳过备份，实际运行时会先备份全部 md")
        else:
            zp, n = backup_md(vault, backup_dir)
            stats["backup"] = zp
            log("已备份 %d 篇笔记 -> %s" % (n, zp))

    # 读取正文
    bodies = {}
    for rel, p, top, subdir, name in notes:
        try:
            raw = open(util.long_path(p), encoding="utf-8", errors="ignore").read()
        except Exception:
            raw = ""
        bodies[rel] = util.strip_generated(util.strip_frontmatter(raw))

    keywords, vocab = {}, []
    related = {}
    write_fails = []

    if do_tags or do_related:
        log("分词与关键词分析中（jieba TF-IDF）…")
        keywords, vocab = analysis.compute_keywords(notes, bodies, vocab_size, min_doc_freq)
        stats["vocab_tags"] = len(vocab)
        log("共享标签词表 %d 个" % len(vocab))

    if do_related:
        log("计算内容相似度中…")
        related = analysis.compute_related(notes, bodies, keywords, min_sim, max_related)

    # 写回笔记
    written = 0
    if do_tags or do_related:
        log("写入笔记 frontmatter / 相关笔记区块…")
        for rel, p, top, subdir, name in notes:
            body = bodies[rel]
            new = body
            if do_tags:
                tags = [top if top != "未分类" else "未分类"]
                if subdir and subdir != top:
                    tags.append(subdir)
                for k in keywords[rel][:top_tags]:
                    if k in vocab:
                        tags.append(k)
                seen, clean_tags = set(), []
                for t in tags:
                    t = util.tag_clean(t)
                    if t and t not in seen:
                        seen.add(t)
                        clean_tags.append(t)
                fm = "---\ntags:\n" + "".join("  - %s\n" % t for t in clean_tags) + "---\n\n"
                new = fm + body.lstrip("\n")
            if do_related and related.get(rel) and util.MARKER not in new:
                lines = ["", util.MARKER, util.GEN_NOTE]
                for other, s in related[rel]:
                    lines.append("- %s · 相似度 %.2f" % (
                        util.safe_link(other, util.pretty(other.split("/")[-1])), s))
                new = new.rstrip() + "\n" + "\n".join(lines) + "\n"
            if not dry_run:
                ok, err = util.write_resilient(p, new)
                if ok:
                    written += 1
                else:
                    write_fails.append("%s | %s" % (rel, err))
        stats["written"] = written
        stats["related_links"] = sum(len(v) for v in related.values())
        stats["notes_with_links"] = len([1 for v in related.values() if v])
        log("已写回 %d 篇，双链 %d 条（覆盖 %d 篇）" % (
            written, stats.get("related_links", 0), stats.get("notes_with_links", 0)))
        if write_fails:
            log("写入失败 %d 篇（文件可能被同步客户端占用）：" % len(write_fails))
            for w in write_fails[:10]:
                log("  " + w)

    # MOC
    if do_moc:
        if dry_run:
            log("[dry-run] 将生成 🏠 知识库总览、各主题 _MOC 枢纽笔记与 🏷 标签索引")
        else:
            mocs = moc_mod.generate_mocs(vault, notes)
            moc_mod.generate_overview(vault, notes)
            tc = moc_mod.generate_tag_index(vault, notes)
            stats["moc_files"] = len(mocs) + 2
            stats["tags_total"] = len(tc)
            log("已生成 %d 个主题枢纽笔记 + 总览 + 标签索引（共 %d 个标签）" % (len(mocs), len(tc)))

    # 视图配置
    if do_graph:
        tops = [n[2] for n in notes if n[2] != "未分类"]
        tops = sorted(set(tops), key=lambda t: -len([n for n in notes if n[2] == t]))
        if dry_run:
            log("[dry-run] 将配置 .obsidian/graph.json 着色分组（%d 个主题）" % len(tops))
        else:
            ok, msg = graphview.write_graph_json(vault, tops, force=graph_force)
            log(msg)

    # 修复遗留问题
    if not dry_run:
        renamed = fixer.fix_filename_spaces(vault)
        if renamed:
            log("已清理 %d 个文件名的首尾空格" % len(renamed))
        nf, fl = fixer.fix_pdf_links(vault)
        if nf:
            log("已修复 %d 条指向 PDF 的旧双链（%d 个文件）" % (nf, len(fl)))
        stats["fixed_links"] = nf

    return stats


def verify_and_print(vault, log=print):
    res = verify(vault)
    log(format_report(res))
    return res
