#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEMS 一键流程：解析原始 CSV → 识别周期峰 → 取末 N 峰 → 出表 → 出图。

用法：
  python dems_pipeline.py                       # 默认读 ./samples
  python dems_pipeline.py --input-dir samples
  python dems_pipeline.py --input-dir D:\数据\261117 --count 3
  python dems_pipeline.py --input-dir samples --skip-plot

输出（名字固定为「输入文件夹名_编号」，编号从 0 开始，已存在就往后顺延）：
  outputs/<输入文件夹名>_0/
    dems_per_file.csv   每条记录
    dems_best.csv       每个样品最终取段与比例尺
    数据对比.md          汇总表
    <样品>.png          三通道 Cycle 图（直接放在这一层）
"""

import argparse
import os
import sys

import yaml

from dems_analysis import analyze_dir, write_tables

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_ROOT = os.path.join(SCRIPT_DIR, "outputs")
# 默认输入目录：仓库自带的 samples/；没有则沿用旧布局的 dems/
_DEFAULT_INPUT = "samples" if os.path.isdir(
    os.path.join(SCRIPT_DIR, "samples")) else "dems"


def load_config(path):
    with open(path, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
    return cfg


def next_run_dir(tag):
    """outputs/<输入文件夹名>_<编号>，编号从 0 开始，取第一个没被占用的。"""
    os.makedirs(OUTPUT_ROOT, exist_ok=True)
    index = 0
    while True:
        path = os.path.join(OUTPUT_ROOT, "%s_%d" % (tag, index))
        if not os.path.exists(path):
            return path
        index += 1


def _parse_window(text, scale):
    """把 "4750:5600" 解析成秒；scale=0.001 时输入按毫秒理解。"""
    cleaned = text.replace(",", "").replace("，", "")
    for sep in (":", "-", "~", "至"):
        if sep in cleaned:
            a, b = cleaned.split(sep, 1)
            break
    else:
        raise SystemExit("区间要写成 T0:T1，例如 4750:5600 或 4750000:5600000")
    try:
        t0, t1 = float(a) * scale, float(b) * scale
    except ValueError:
        raise SystemExit("区间里的数字看不懂：%s" % text)
    if t0 > t1:
        t0, t1 = t1, t0
    return (t0, t1)


def main(argv=None):
    parser = argparse.ArgumentParser(description="DEMS 三通道 Cycle 图")
    parser.add_argument("--input-dir",
                        default=os.path.join(SCRIPT_DIR, _DEFAULT_INPUT),
                        help="原始 HAL CSV 所在目录（默认 ./samples，其次 ./dems）")
    parser.add_argument("--output-dir", default=None,
                        help="输出目录（默认 output/<标签>_0）")
    parser.add_argument("--tag", default=None,
                        help="输出子目录名前缀（默认用输入目录名）")
    parser.add_argument("--config", default=os.path.join(SCRIPT_DIR, "config.yaml"))
    parser.add_argument("--window", default=None, metavar="T0:T1",
                        help="指定取段（秒），如 4750:5600；给了就不用取末 N 峰的规则")
    parser.add_argument("--window-ms", default=None, metavar="T0:T1",
                        help="同上，单位毫秒（Origin 里的时间轴），如 4750000:5600000")
    parser.add_argument("--count", type=int, default=None,
                        help="取几个峰（覆盖 config.yaml 的 peaks.count），如 --count 3")
    parser.add_argument("--keep-suffix", action="store_true",
                        help="样品名完全用文件名，不剥掉 -FileNNN 之类的后缀")
    parser.add_argument("--exclude", action="append", default=[], metavar="PATTERN",
                        help="跳过文件名匹配这个通配符的 CSV，可写多次，如 --exclude \"*18O*\"")
    parser.add_argument("--zoom", action="append", default=[], metavar="MZ:VALUE",
                        help="覆盖某个通道的纵轴放大倍数，可写多次，如 --zoom 34:1 --zoom 36:1")
    parser.add_argument("--skip-plot", action="store_true", help="只出表，不出图")
    args = parser.parse_args(argv)

    cfg = load_config(os.path.abspath(args.config))
    if args.count:
        cfg.setdefault("peaks", {})["count"] = int(args.count)
    if args.keep_suffix:
        cfg.setdefault("naming", {})["strip_suffix"] = False
    if args.exclude:
        cfg["exclude"] = list(args.exclude)
    for item in args.zoom:
        mz_text, value = item.split(":", 1)
        for channel in cfg["channels"]:
            if int(channel["mz"]) == int(mz_text):
                channel["zoom"] = float(value)

    window = None
    if args.window_ms:
        window = _parse_window(args.window_ms, 0.001)
    elif args.window:
        window = _parse_window(args.window, 1.0)
    if window:
        cfg["window"] = window

    input_dir = os.path.abspath(args.input_dir)
    if not os.path.isdir(input_dir):
        parser.error("找不到输入目录：%s" % input_dir)

    records, errors = analyze_dir(input_dir, cfg)
    for path, message in errors:
        print("跳过：%s（%s）" % (os.path.basename(path), message))
    if not records:
        print("")
        print("没有可用的 CSV：%s" % input_dir)
        if not errors:
            print("  该目录里没有 .csv 文件。")
        print("  每个 CSV 里要有一行以 Time 开头的表头，后面跟各质量通道，例如：")
        print('    "Time","ms","Scan 1 : mass 32.00","Scan 2 : mass 34.00",...')
        print("    Time,ms,mass 32,mass 34,mass 36")
        print("  数据行第一列是时间（HH:MM:SS 或秒），其余列是信号；表头行数、")
        print("  分隔符、列顺序都按文件内容自动识别。示例见：%s"
              % os.path.join(SCRIPT_DIR, "samples"))
        return 1

    tag = (args.tag
           or (cfg.get("output") or {}).get("tag")
           or os.path.basename(input_dir.rstrip("\\/")))
    out_dir = args.output_dir or next_run_dir(tag)
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    write_tables(records, out_dir, cfg)
    print("已生成：%s" % os.path.join(out_dir, "dems_per_file.csv"))
    print("已生成：%s" % os.path.join(out_dir, "dems_best.csv"))
    print("已生成：%s" % os.path.join(out_dir, "数据对比.md"))

    chans = [int(c["mz"]) for c in cfg["channels"]]
    for rec in records:
        line = "%-6s %-22s 峰 %2d/%2d  窗口 %.0f–%.0f s" % (
            rec["name"], rec["file"], rec["n_used"], rec["n_found"],
            rec["window"][0], rec["window"][1])
        line += "  比例尺 " + " / ".join(
            "m/z%d %s" % (mz, rec["bars"][mz]["text"]) for mz in chans)
        print(line)
        for warning in rec["warnings"]:
            print("   警告：%s" % warning)

    if not args.skip_plot:
        try:
            import dems_plot
        except ImportError:
            print("缺少绘图依赖（matplotlib）。请先双击 安装依赖.bat，"
                  "或加 --skip-plot 只出表。")
            return 1
        fig_dir = out_dir
        for rec in records:
            path = os.path.join(fig_dir, rec["name"] + ".png")
            try:
                dems_plot.plot_sample(rec, cfg, path)
                print("已生成：%s" % path)
            except PermissionError:
                print("写入失败，文件可能正被占用：%s" % path)
                return 1

    print("输出目录：%s" % out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
