#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEMS 一键流程：解析原始 CSV → 识别周期峰 → 取末 N 峰 → 出表 → 出图。

用法：
  python dems_pipeline.py                       # 默认读 ./samples
  python dems_pipeline.py --input-dir samples
  python dems_pipeline.py --input-dir samples --tag 20261013-dems
  python dems_pipeline.py --input-dir samples --skip-plot

输出：
  output/<标签>_0/
    dems_per_file.csv   每条记录
    dems_best.csv       每个样品最终取段与比例尺
    数据对比.md          汇总表
    图/<样品>.png        三通道 Cycle 图
"""

import argparse
import os
import sys

import yaml

from dems_analysis import analyze_dir, write_tables

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 默认输入目录：仓库自带的 samples/；没有则沿用旧布局的 dems/
_DEFAULT_INPUT = "samples" if os.path.isdir(
    os.path.join(SCRIPT_DIR, "samples")) else "dems"


def load_config(path):
    with open(path, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
    return cfg


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
    parser.add_argument("--skip-plot", action="store_true", help="只出表，不出图")
    args = parser.parse_args(argv)

    cfg = load_config(os.path.abspath(args.config))

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
    out_dir = args.output_dir or os.path.join(SCRIPT_DIR, "output", tag + "_0")
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
        fig_dir = os.path.join(out_dir, "图")
        os.makedirs(fig_dir, exist_ok=True)
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
