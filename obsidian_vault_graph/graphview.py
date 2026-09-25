# -*- coding: utf-8 -*-
"""图谱视图配置：.obsidian/graph.json 的着色分组与力学参数"""
import json
import os
import shutil


def hex_to_int(h):
    h = h.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return r * 65536 + g * 256 + b


DEFAULT_PALETTE = [
    "#4C6EF5", "#12B886", "#FA5252", "#FD7E14", "#BE4BDB", "#15AABF",
    "#F59F00", "#E64980", "#7048E8", "#228BE6", "#868E96", "#40C057",
    "#20C997", "#F76707", "#3BC9DB", "#C92A2A",
]

DEFAULT_SETTINGS = {
    "collapse-filter": False,
    "search": "",
    "showTags": True,
    "showAttachments": False,
    "hideUnresolved": True,
    "showOrphans": True,
    "collapse-color-groups": False,
    "collapse-display": False,
    "showArrow": True,
    "textFadeMultiplier": -0.5,
    "nodeSizeMultiplier": 1.2,
    "lineSizeMultiplier": 0.7,
    "collapse-forces": False,
    "centerStrength": 0.45,
    "repelStrength": 12,
    "linkStrength": 1,
    "linkDistance": 200,
    "scale": 0.1,
    "close": False,
}


def write_graph_json(vault, top_folders=None, palette=None, force=False):
    """为 vault 写入 .obsidian/graph.json（旧配置自动备份为 .bak_before_ovg）"""
    gd = os.path.join(os.path.abspath(vault), ".obsidian")
    if not os.path.isdir(gd):
        return False, "该目录不是 Obsidian 库（缺少 .obsidian），跳过视图配置"
    path = os.path.join(gd, "graph.json")
    if os.path.exists(path) and not force:
        try:
            with open(path, encoding="utf-8") as f:
                old = json.load(f)
            if old.get("colorGroups"):
                return False, "graph.json 已有颜色分组，未覆盖（如需覆盖使用 --force）"
        except Exception:
            pass
    shutil.copy2(path, os.path.join(gd, "graph.json.bak_before_ovg"))

    top_folders = top_folders or []
    palette = palette or DEFAULT_PALETTE
    groups = [{"query": "file:_MOC OR file:知识库总览 OR file:标签索引",
               "color": {"a": 1, "rgb": hex_to_int("#F6AD55")}}]
    for i, folder in enumerate(top_folders):
        c = palette[i % len(palette)]
        groups.append({"query": "path:%s" % folder, "color": {"a": 1, "rgb": hex_to_int(c)}})

    cfg = dict(DEFAULT_SETTINGS)
    cfg["colorGroups"] = groups
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return True, "已写入 %s（%d 个着色分组）" % (path, len(groups))
