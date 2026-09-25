# -*- coding: utf-8 -*-
"""通用工具：路径、安全写入、链接语法、文本清洗"""
import os
import re
import stat
import time
import urllib.parse

MARKER = "## 相关笔记"
GEN_NOTE = "> 由 obsidian-vault-graph 自动生成"

SKIP_DIRS = {".obsidian", ".workbuddy", ".git", ".trash", "node_modules"}

STOPWORDS = set("""的 了 和 是 在 我 有 就 不 人 都 一 一个 上 也 很 到 说 要 去 你 会 着 没有 看 好 自己 这 那 他 她 它 们 与 及 或 而 但 因为 所以 如果 就是 可以 这个 那个 什么 时候 大家 我们 你们 他们 一些 以及 通过 对于 关于 需要 可能 一般 主要 包括 进行 使用 已经 还要 但是 而且 或者 下面 以上 如下 注意 介绍 分享 推荐 下载 查看 内容 笔记 方法 问题 时间 图片 视频 网站 网页 链接 百度 点击 相关 更 最 还 又 再 只 把 被 让 从 向 对 为 以 之 其 其他 每个 各种 不同 非常 比较 最好 应该 不能 不会 不是 只是 还是 例如 比如 由于 因此 不过 虽然 然后 现在 目前 之后 之前 上面 里面 这些 那些 这样 那样 多少 怎么 为什么 哪个 哪些 何时 何地""".split())

NOISE = set("""note assets asset png jpg jpeg gif bmp webp com cn net org http https www html htm pdf md txt doc docs docx
xls xlsx ppt pptx bak src img image div span style color font width height align class id true false yes
null none data file files name type value text new old copy temp tmp cache app apps user admin login
update install setup error warn log logs line page pages section index list items item out out1
check test demo sample version beta alpha url uri link links click here there this that and the for with from
you your our its don't can't will would could should about above after again""".split())

BLACKLIST_WORDS = set()


def long_path(p):
    """Windows 下为绝对路径添加长路径前缀，以支持超过 260 字符的路径"""
    if os.name == "nt" and not str(p).startswith("\\\\?\\"):
        return "\\\\?\\" + os.path.abspath(str(p))
    return p


def write_resilient(path, content, retries=5):
    """安全写入：文件被同步客户端/杀软短暂占用时自动重试"""
    last = None
    for _ in range(retries):
        try:
            if os.path.exists(long_path(path)):
                try:
                    os.chmod(long_path(path), stat.S_IWRITE)
                except Exception:
                    pass
            with open(long_path(path), "w", encoding="utf-8") as f:
                f.write(content)
            return True, ""
        except Exception as e:
            last = e
            time.sleep(1.0)
    return False, str(last)


def list_notes(vault):
    """列出库内全部 md 笔记，返回 [(rel_no_ext, abs_path, top_folder, sub_dir, filename)]"""
    result = []
    vault = os.path.abspath(vault)
    for dirpath, dirnames, filenames in os.walk(vault):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not fn.lower().endswith(".md"):
                continue
            if fn.startswith("_MOC ") or fn in ("🏠 知识库总览.md", "🏷 标签索引.md"):
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, vault).replace("\\", "/")[:-3]
            parts = rel.split("/")
            top = parts[0] if len(parts) > 1 else "未分类"
            subdir = "/".join(parts[:-1]) if len(parts) > 1 else ""
            result.append((rel, p, top, subdir, parts[-1]))
    return result


def esc(name):
    for ch in "#|[]^":
        name = name.replace(ch, "\\" + ch)
    return name


def pretty(name):
    """显示名美化：去掉导出工具留下的 .note 等后缀"""
    for suf in (".note", ".cn", ".note.attach"):
        if name.endswith(suf):
            return name[: -len(suf)]
    return name


def safe_link(rel_no_ext, alias):
    """文件名含 # | [ ] ^ 时使用 URL 编码的 markdown 链接，否则用 wikilink"""
    name = rel_no_ext.split("/")[-1]
    if re.search(r"[#\[\]\|\^]", name):
        url = "/".join(urllib.parse.quote(x) for x in rel_no_ext.split("/")) + ".md"
        a = alias.replace("[", "\\[").replace("]", "\\]").replace("|", "\\|")
        return "[%s](%s)" % (a, url)
    return "[[%s|%s]]" % (rel_no_ext, alias)


def tag_clean(t):
    return re.sub(r"[#\[\]\|\^]", "", str(t)).strip().replace(" ", "-")


def strip_frontmatter(txt):
    if txt.startswith("---"):
        m = re.match(r"^---\r?\n.*?\r?\n---\r?\n?", txt, re.S)
        if m:
            return txt[m.end():]
    return txt


def strip_generated(txt):
    """剥掉本工具上次生成的相关笔记区块，保证幂等"""
    return txt.split(MARKER)[0].rstrip()


def clean_for_nlp(txt):
    """清洗转换产物噪音：图片/链接语法、URL、自动生成区块"""
    txt = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", txt)
    txt = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", txt)
    txt = re.sub(r"\[\[([^\]\|]*)\|?[^\]]*\]\]", r"\1", txt)
    txt = txt.split(MARKER)[0]
    txt = re.sub(r"https?://\S+", " ", txt)
    return txt


def ok_token(w):
    w = w.strip()
    if len(w) < 2 or w in STOPWORDS or w in NOISE or w in BLACKLIST_WORDS:
        return False
    if re.fullmatch(r"[\d\W_]+", w):
        return False
    if re.fullmatch(r"[A-Za-z]{1,3}\d*", w):
        return False
    if re.fullmatch(r"[A-Za-z]+\d+", w):
        return False
    return True


def norm_title(name):
    """归一化标题用于副本去重"""
    n = pretty(name).lower()
    n = re.sub(r"[\s\-_·、,，.。:：;；!！?？()（）\[\]【】]+", "", n)
    n = re.sub(r"(副本|copy|\d+)$", "", n)
    return n
