# -*- coding: utf-8 -*-
"""ovg 命令行入口"""
import argparse
import sys

from . import __version__
from .builder import build, verify_and_print
from . import moc as moc_mod, fixer


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="ovg",
        description="obsidian-vault-graph · 为 Obsidian 库一键建立关系图谱（标签 / 相关性双链 / MOC 枢纽 / 图谱视图配色）")
    ap.add_argument("--version", action="version", version="ovg %s" % __version__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_vault_arg(p, help_text="Obsidian 库根目录"):
        p.add_argument("vault", help=help_text)

    p_build = sub.add_parser("build", help="一键建图：备份→标签→相关性双链→MOC→图谱视图配置")
    add_vault_arg(p_build)
    p_build.add_argument("--dry-run", action="store_true", help="只演示将要做什么，不写任何文件")
    p_build.add_argument("--no-backup", action="store_true", help="跳过 md 备份（不推荐）")
    p_build.add_argument("--backup-dir", default=None, help="备份 zip 的输出目录（默认库的上级目录）")
    p_build.add_argument("--vocab-size", type=int, default=90, help="共享标签词表大小（默认 90）")
    p_build.add_argument("--min-doc-freq", type=int, default=8, help="关键词进入词表的最低笔记数（默认 8）")
    p_build.add_argument("--top-tags", type=int, default=3, help="每篇笔记最多注入的内容标签数（默认 3）")
    p_build.add_argument("--min-sim", type=float, default=0.28, help="相关性双链的相似度阈值（默认 0.28）")
    p_build.add_argument("--max-related", type=int, default=3, help="每篇笔记最多相关笔记数（默认 3）")
    p_build.add_argument("--skip-tags", action="store_true", help="跳过标签注入")
    p_build.add_argument("--skip-related", action="store_true", help="跳过相关性双链")
    p_build.add_argument("--skip-moc", action="store_true", help="跳过 MOC 枢纽笔记生成")
    p_build.add_argument("--skip-graph", action="store_true", help="跳过 graph.json 视图配置")
    p_build.add_argument("--graph-force", action="store_true", help="覆盖已有的 graph.json 颜色分组")

    p_verify = sub.add_parser("verify", help="校验：frontmatter 覆盖率、链接解析、标签统计")
    add_vault_arg(p_verify)

    p_moc = sub.add_parser("moc", help="只重新生成 MOC 枢纽笔记 / 总览 / 标签索引")
    add_vault_arg(p_moc)

    p_fix = sub.add_parser("fix", help="修复：指向 PDF 的旧双链、文件名首尾空格")
    add_vault_arg(p_fix)

    args = ap.parse_args(argv)

    if args.cmd == "build":
        try:
            build(args.vault,
                  dry_run=args.dry_run,
                  no_backup=args.no_backup,
                  backup_dir=args.backup_dir,
                  vocab_size=args.vocab_size,
                  min_doc_freq=args.min_doc_freq,
                  top_tags=args.top_tags,
                  min_sim=args.min_sim,
                  max_related=args.max_related,
                  do_tags=not args.skip_tags,
                  do_related=not args.skip_related,
                  do_moc=not args.skip_moc,
                  do_graph=not args.skip_graph,
                  graph_force=args.graph_force)
        except Exception as e:
            print("错误: %s" % e, file=sys.stderr)
            return 1
        print("\n完成。在 Obsidian 中重新打开该库，按 Ctrl+G 查看关系图谱。")
        return 0

    if args.cmd == "verify":
        verify_and_print(args.vault)
        return 0

    if args.cmd == "moc":
        notes = __import__("obsidian_vault_graph.util", fromlist=["list_notes"]).list_notes(args.vault)
        made = moc_mod.generate_mocs(args.vault, notes)
        moc_mod.generate_overview(args.vault, notes)
        tc = moc_mod.generate_tag_index(args.vault, notes)
        print("已生成 %d 个主题枢纽 + 总览 + 标签索引（%d 个标签）" % (len(made), len(tc)))
        return 0

    if args.cmd == "fix":
        renamed = fixer.fix_filename_spaces(args.vault)
        print("清理文件名首尾空格：%d 个" % len(renamed))
        nf, fl = fixer.fix_pdf_links(args.vault)
        print("修复指向 PDF 的旧双链：%d 条（%d 个文件）" % (nf, len(fl)))
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
