#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEMS CSV 解析、周期峰识别、取段与结果表。

输入格式不写死：自动找以 Time 开头的表头行，分隔符（`,` `;` tab）、时间写法
（HH:MM:SS / H:MM:SS / M:SS / 秒）、通道标注（`mass 32.00`、`m/z 34`）都按内容识别；
表头没写 m/z 时按出现顺序当作 32、34、36。不扣背景、不平滑、不重采样。

对外函数：
  read_hal(path)                → 单文件原始数据
  analyze_dir(input_dir, cfg)   → 每个样品一条记录（含取段、统计、比例尺）
  write_tables(records, out_dir, cfg)
"""

import csv
import math
import os
import re

import numpy as np

TIME_NAMES = ("time", "时间")
MASS_RE = re.compile(r"(?:mass|m/z|mz)\s*([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)
DELIMITERS = (",", ";", "\t")
IGNORED_NAMES = ("ms", "", "index", "point", "scan", "no", "no.")


def sample_name(path, strip_suffix=True):
    """由源文件名推导输出名，首字母大写。

    strip_suffix=True 时去掉 -File245 这类后缀；False 就整段保留。
    """
    stem = os.path.splitext(os.path.basename(path))[0]
    if strip_suffix:
        stem = re.sub(r"-file\d+$", "", stem, flags=re.IGNORECASE)
    if not stem:
        stem = os.path.splitext(os.path.basename(path))[0]
    return stem[0].upper() + stem[1:]


def _split(line, delim=","):
    return [p.strip().strip('"').strip() for p in line.strip().split(delim)]


def _find_table(lines):
    """找数据表：第一列是 Time 的那一行。表头行数、分隔符都不写死。

    返回 (数据起始行, 分隔符, 表头字段)。
    """
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        best = None
        for delim in DELIMITERS:
            fields = _split(line, delim)
            if fields and fields[0].lower() in TIME_NAMES:
                if best is None or len(fields) > len(best[1]):
                    best = (delim, fields)
        if best:
            return i + 1, best[0], best[1]
    raise ValueError("找不到数据表（没有以 Time 开头的表头行）")


def _map_columns(header, fallback_masses):
    """从表头推时间列和各信号列对应的 m/z。

    表头写了 mass 32.00 / m/z 34 就按写的来；没写就按 fallback 顺序对应。
    """
    time_idx = None
    for i, name in enumerate(header):
        if name.lower() in TIME_NAMES:
            time_idx = i
            break
    if time_idx is None:
        raise ValueError("表头里没有时间列")

    masses, signal_idx, unnamed = [], [], []
    for i, name in enumerate(header):
        if i == time_idx:
            continue
        match = MASS_RE.search(name)
        if match:
            mz = int(round(float(match.group(1))))
            if mz not in masses:
                masses.append(mz)
                signal_idx.append(i)
        elif name.lower() in IGNORED_NAMES:
            continue
        else:
            unnamed.append(i)

    if not masses:
        masses = list(fallback_masses)[:len(unnamed)]
        signal_idx = unnamed[:len(masses)]
    if not signal_idx:
        raise ValueError("表头里没有信号列")
    return time_idx, signal_idx, masses


def _parse_time(text):
    """时间：HH:MM:SS、H:MM:SS、M:SS 或直接给秒。"""
    text = text.strip().strip('"')
    if not text:
        raise ValueError("空时间")
    if ":" in text:
        nums = [float(p) for p in text.split(":")]
        if len(nums) == 3:
            return nums[0] * 3600.0 + nums[1] * 60.0 + nums[2]
        if len(nums) == 2:
            return nums[0] * 60.0 + nums[1]
        raise ValueError("时间格式：%s" % text)
    return float(text)


def _start_time(lines):
    """记录起始时刻：表头里 Date 后面那个 Time 值，没有就留空。"""
    for line in lines[:80]:
        parts = _split(line)
        names = [p.lower() for p in parts]
        if "date" in names and "time" in names:
            i = names.index("time")
            if i + 1 < len(parts):
                return parts[i + 1]
    return ""


def read_hal(path, fallback_masses=(32, 34, 36)):
    """读一个 CSV：自动识别表头、分隔符、时间列和各信号列的 m/z。

    返回 dict：time(s), t_start, duration_min, channels{mz: array}, masses。
    """
    with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
        lines = fh.readlines()
    if not lines:
        raise ValueError("空文件")

    data_start, delim, header = _find_table(lines)
    time_idx, signal_idx, masses = _map_columns(header, fallback_masses)

    rows = []
    last_col = max([time_idx] + signal_idx)
    for line in lines[data_start:]:
        if not line.strip():
            continue
        parts = _split(line, delim)
        if len(parts) <= last_col:
            continue
        try:
            t = _parse_time(parts[time_idx])
            values = [float(parts[i]) for i in signal_idx]
        except ValueError:
            continue
        rows.append([t] + values)

    if not rows:
        raise ValueError("没有解析到数据行")

    arr = np.array(rows, dtype=float)
    time = arr[:, 0]
    channels = {m: arr[:, 1 + i] for i, m in enumerate(masses)}
    return {
        "time": time,
        "t_start": _start_time(lines),
        "duration_min": (time[-1] - time[0]) / 60.0,
        "channels": channels,
        "masses": masses,
    }


def rolling_median(v, win):
    half = win // 2
    out = np.empty_like(v)
    for i in range(len(v)):
        lo, hi = max(0, i - half), min(len(v), i + half + 1)
        out[i] = np.median(v[lo:hi])
    return out


def detrend_points(time, cfg):
    """去趋势窗口点数：配置写秒数时按实际采样间隔换算，写成点数就直接用。"""
    peaks_cfg = cfg["peaks"]
    if peaks_cfg.get("detrend_seconds") is not None:
        dt = float(np.median(np.diff(time))) if len(time) > 1 else 0.0
        win = int(round(float(peaks_cfg["detrend_seconds"]) / dt)) if dt > 0 else 41
    else:
        win = int(peaks_cfg["detrend_window"])
    win = max(3, win)
    if win % 2 == 0:
        win += 1
    return min(win, max(3, len(time) // 2 * 2 + 1))


def find_peaks(time, v32, cfg):
    """滚动中位数去趋势后找 m/z 32 周期峰，返回峰索引。"""
    win = detrend_points(time, cfg)
    gap = float(cfg["peaks"]["min_gap_seconds"])
    prom = float(cfg["peaks"]["min_prominence"])

    resid = v32 - rolling_median(v32, win)
    cand = []
    for i in range(1, len(v32) - 1):
        if resid[i] > prom and resid[i] >= resid[i - 1] and resid[i] > resid[i + 1]:
            cand.append(i)

    picked = []
    for i in cand:
        if picked and time[i] - time[picked[-1]] < gap:
            if resid[i] > resid[picked[-1]]:
                picked[-1] = i
        else:
            picked.append(i)
    return picked, resid


def select_peaks(peaks, time, count, cfg):
    """从识别到的峰里取 count 个：优先取末尾一段间距规整的。

    返回 (峰索引列表, 警告或 None)。
    """
    peaks = list(peaks)
    if len(peaks) <= count:
        return peaks, None
    if not bool(cfg["peaks"].get("require_regular", True)):
        return peaks[-count:], None

    tol = float(cfg["peaks"].get("gap_tolerance", 1.3))
    best = None
    for i in range(len(peaks) - count + 1):
        window = peaks[i:i + count]
        gaps = np.diff(time[window])
        if gaps.min() <= 0:
            continue
        if gaps.max() / gaps.min() <= tol:
            best = window  # 越靠后的窗口会覆盖前面的，最后留下最晚的一段
    if best is not None:
        if best[-1] != peaks[-1]:
            skipped = len(peaks) - peaks.index(best[-1]) - 1
            return best, ("末尾 %d 个峰间距不规整，已取最后一段间距一致的 %d 个峰"
                          "（%.0f–%.0f s）" % (skipped, count,
                                              time[best[0]], time[best[-1]]))
        return best, None

    window = peaks[-count:]
    gaps = np.diff(time[window])
    return window, ("没找到间距一致的 %d 个峰（末尾一段 %.0f–%.0f s），仍按最后 %d 个出图"
                    % (count, gaps.min(), gaps.max(), count))


def cycle_axis(time, centers):
    c0, c1 = centers[0], centers[-1]
    return 1.0 + (len(centers) - 1.0) * (time - c0) / (c1 - c0)


def bar_number(value, decimals=1):
    exp = math.floor(math.log10(value))
    mant = round(value / (10.0 ** exp), decimals)
    if mant >= 10.0:
        mant, exp = 1.0, exp + 1
    return mant, exp


def fmt_bar(mant, exp, decimals=1):
    return ("%.*f" % (decimals, mant)) + " × 10^%d" % exp


def analyze_file(path, cfg):
    wanted_mz = [int(ch["mz"]) for ch in cfg["channels"]]
    raw = read_hal(path, fallback_masses=wanted_mz)
    time = raw["time"]
    channels = raw["channels"]

    need = list(dict.fromkeys(wanted_mz + [32]))
    missing = [mz for mz in need if mz not in channels]
    if missing:
        raise ValueError("文件里只有 m/z %s，缺少 m/z %s" % (
            "、".join(str(m) for m in sorted(channels)),
            "、".join(str(m) for m in missing)))

    v32 = channels[32]

    peaks, _ = find_peaks(time, v32, cfg)
    cfg_sample = (cfg.get("samples") or {}).get(os.path.basename(path)) or {}
    warnings = []

    if not peaks:
        raise ValueError("没有识别到 m/z 32 周期峰")

    # 指定区间优先：给了 window 就直接按它取段，不再用"取末 N 峰"的规则
    window = cfg_sample.get("window") or cfg.get("window")
    if window:
        t0, t1 = float(window[0]), float(window[1])
        if t0 > t1:
            t0, t1 = t1, t0
        if t0 >= time[-1] or t1 <= time[0]:
            raise ValueError("指定区间 %.0f–%.0f s 不在记录范围 %.0f–%.0f s 内"
                             % (t0, t1, time[0], time[-1]))
        inside = [p for p in peaks if t0 <= time[p] <= t1]
        if not inside:
            raise ValueError("指定区间 %.0f–%.0f s 里没有认到 m/z 32 周期峰，"
                             "换个区间或调低 peaks.min_prominence" % (t0, t1))
        if t0 < time[0] or t1 > time[-1]:
            warnings.append("指定区间超出记录范围，已截到 %.0f–%.0f s"
                            % (max(t0, time[0]), min(t1, time[-1])))
        t0, t1 = max(t0, time[0]), min(t1, time[-1])
        centers = time[inside]
        count = len(centers)
        warnings.append("按指定区间取段：%.0f–%.0f s，含 %d 个峰" % (t0, t1, count))
    else:
        wanted = int(cfg["peaks"]["count"])
        count = int(cfg_sample.get("peaks", wanted))
        if len(peaks) < count:
            warnings.append("只识别到 %d 个峰，按 %d 个出图" % (len(peaks), len(peaks)))
            count = len(peaks)
        chosen, hint = select_peaks(peaks, time, count, cfg)
        if hint:
            warnings.append(hint)
        centers = time[chosen]
        count = len(centers)
        pad = float(cfg["peaks"]["pad_seconds"])
        t0, t1 = centers[0] - pad, centers[-1] + pad
        if t0 < time[0]:
            warnings.append("首峰前留白不足，窗口从记录起点开始")
            t0 = time[0]
        if t1 > time[-1]:
            warnings.append("末峰后留白不足，窗口到记录终点为止")
            t1 = time[-1]

    if count >= 3:
        gaps = np.diff(centers)
        if gaps.min() > 0 and gaps.max() / gaps.min() > 1.5:
            warnings.append(
                "取用峰间距不均（%.0f–%.0f s），可能不是等周期循环，取段需人工确认"
                % (gaps.min(), gaps.max()))

    mask = (time >= t0) & (time <= t1)
    x = cycle_axis(time[mask], centers)

    layout = cfg["layout"]
    bottom = float(layout["data_bottom"])
    top = float(layout["data_top"])

    stats = {}
    bars = {}
    for ch in cfg["channels"]:
        mz = int(ch["mz"])
        vals = channels[mz][mask]
        lo, hi = float(vals.min()), float(vals.max())
        span = hi - lo if hi > lo else 1.0
        total = span / (top - bottom) * float(ch["zoom"])
        ymin = lo - bottom * total
        ymax = ymin + total

        value = float(cfg["scale_bar"]["height"]) * (ymax - ymin)
        mant, exp = bar_number(value, int(cfg["scale_bar"]["decimals"]))

        stats[mz] = {"min": lo, "max": hi, "range": hi - lo,
                     "total": total, "ylim": (ymin, ymax)}
        bars[mz] = {"mant": mant, "exp": exp,
                    "text": fmt_bar(mant, exp,
                                    int(cfg["scale_bar"]["decimals"]))}

    strip = bool((cfg.get("naming") or {}).get("strip_suffix", True))
    name = cfg_sample.get("name") or sample_name(path, strip_suffix=strip)
    return {
        "path": path,
        "file": os.path.basename(path),
        "name": name,
        "t_start": raw["t_start"],
        "duration_min": raw["duration_min"],
        "n_found": len(peaks),
        "n_used": count,
        "centers": centers,
        "window": (t0, t1),
        "x": x,
        "vals": {int(ch["mz"]): channels[int(ch["mz"])][mask]
                 for ch in cfg["channels"]},
        "stats": stats,
        "bars": bars,
        "warnings": warnings,
    }


def analyze_dir(input_dir, cfg):
    files = []
    for root, _, names in os.walk(input_dir):
        for name in sorted(names):
            if name.lower().endswith(".csv"):
                files.append(os.path.join(root, name))

    records, errors = [], []
    for path in files:
        try:
            records.append(analyze_file(path, cfg))
        except Exception as exc:  # noqa: BLE001 - 汇总后统一报告
            errors.append((path, str(exc)))

    order = {name: i for i, name in enumerate((cfg.get("samples") or {}).keys())}
    records.sort(key=lambda r: (order.get(r["file"], 10 ** 6), r["file"]))
    _dedupe_names(records)
    share_scales(records, cfg)
    return records, errors


def share_scales(records, cfg):
    """所有样品共用同一段比例尺：同通道取各样品里最大的一段。

    这样三个样品的 m/z 32 比例尺数值相同、34 相同、36 相同，可以直接比峰高。
    """
    if not (cfg.get("scale_bar") or {}).get("shared"):
        return
    chans = [int(c["mz"]) for c in cfg["channels"]]
    bottom = float(cfg["layout"]["data_bottom"])
    height = float(cfg["scale_bar"]["height"])
    decimals = int(cfg["scale_bar"]["decimals"])
    shared = {mz: max(r["stats"][mz]["total"] for r in records) for mz in chans}
    for rec in records:
        for mz in chans:
            st = rec["stats"][mz]
            total = shared[mz]
            ymin = st["min"] - bottom * total
            st["total"] = total
            st["ylim"] = (ymin, ymin + total)
            mant, exp = bar_number(height * total, decimals)
            rec["bars"][mz] = {"mant": mant, "exp": exp,
                               "text": fmt_bar(mant, exp, decimals)}


def _dedupe_names(records):
    """不同文件推出同一个样品名时（如 ru.csv 和 ru-File244.csv），用文件名区分。"""
    used = set()
    for rec in records:
        name = rec["name"]
        if name in used:
            stem = os.path.splitext(rec["file"])[0]
            base = name if stem.lower() == name.lower() else "%s_%s" % (name, stem)
            new, k = base, 2
            while new in used:
                new = "%s_%d" % (base, k)
                k += 1
            rec["warnings"].append("样品名 %s 与别的文件重复，改用 %s" % (name, new))
            rec["name"] = new
            name = new
        used.add(name)


def write_tables(records, out_dir, cfg):
    os.makedirs(out_dir, exist_ok=True)
    chans = [int(c["mz"]) for c in cfg["channels"]]

    per_file = os.path.join(out_dir, "dems_per_file.csv")
    fields = ["文件", "样品名", "记录起始", "记录时长/min", "m/z32峰数",
              "取用峰数", "峰心时刻/s", "窗口起/s", "窗口止/s"]
    for mz in chans:
        fields += ["m/z%d最小值" % mz, "m/z%d最大值" % mz, "m/z%d范围" % mz]
    for mz in chans:
        fields += ["比例尺 m/z%d" % mz]
    fields += ["警告"]

    with open(per_file, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for rec in records:
            row = {
                "文件": rec["file"],
                "样品名": rec["name"],
                "记录起始": rec["t_start"],
                "记录时长/min": "%.1f" % rec["duration_min"],
                "m/z32峰数": rec["n_found"],
                "取用峰数": rec["n_used"],
                "峰心时刻/s": " ".join("%.0f" % c for c in rec["centers"]),
                "窗口起/s": "%.0f" % rec["window"][0],
                "窗口止/s": "%.0f" % rec["window"][1],
                "警告": "；".join(rec["warnings"]),
            }
            for mz in chans:
                st = rec["stats"][mz]
                row["m/z%d最小值" % mz] = "%.3e" % st["min"]
                row["m/z%d最大值" % mz] = "%.3e" % st["max"]
                row["m/z%d范围" % mz] = "%.3e" % st["range"]
            for mz in chans:
                row["比例尺 m/z%d" % mz] = rec["bars"][mz]["text"]
            writer.writerow(row)

    best = os.path.join(out_dir, "dems_best.csv")
    best_fields = ["样品名", "文件", "取用峰数", "峰心时刻/s", "窗口起/s",
                   "窗口止/s"]
    for mz in chans:
        best_fields += ["比例尺 m/z%d" % mz]
    best_fields += ["图", "警告"]
    with open(best, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=best_fields)
        writer.writeheader()
        for rec in records:
            row = {
                "样品名": rec["name"],
                "文件": rec["file"],
                "取用峰数": rec["n_used"],
                "峰心时刻/s": " ".join("%.0f" % c for c in rec["centers"]),
                "窗口起/s": "%.0f" % rec["window"][0],
                "窗口止/s": "%.0f" % rec["window"][1],
                "图": os.path.join("图", rec["name"] + ".png"),
                "警告": "；".join(rec["warnings"]),
            }
            for mz in chans:
                row["比例尺 m/z%d" % mz] = rec["bars"][mz]["text"]
            writer.writerow(row)

    _write_markdown(records, out_dir, cfg)
    return per_file, best


def _write_markdown(records, out_dir, cfg):
    chans = [int(c["mz"]) for c in cfg["channels"]]
    path = os.path.join(out_dir, "数据对比.md")
    lines = ["# DEMS 数据对比", ""]
    head = "| 样品 | 源文件 | m/z 32 峰数 | 取用峰数 | 取段 (s) |"
    for mz in chans:
        head += " 比例尺 m/z %d |" % mz
    lines.append(head)
    lines.append("|---|---|---:|---:|---|---|---|---|")
    for rec in records:
        row = "| %s | %s | %d | %d | %.0f–%.0f |" % (
            rec["name"], rec["file"], rec["n_found"], rec["n_used"],
            rec["window"][0], rec["window"][1])
        for mz in chans:
            row += " %s |" % rec["bars"][mz]["text"]
        lines.append(row)

    zooms = {int(c["mz"]): float(c["zoom"]) for c in cfg["channels"]}
    lines += [
        "",
        "说明：",
        "",
        "- 横轴 `Cycle` 是 m/z 32 峰的序号，并没有与同步 CV 电位做严格对齐；"
        "本次 DEMS 没有同步电化学文件。",
        "- 每张图的纵轴按该样品自身数据范围铺排，比例尺数值各不相同，"
        "不同样品之间不能直接按峰高比较。",
        "- 比例尺为“工”字段，长度固定，数值保留一位小数。",
    ]
    zoom_note = [mz for mz, z in zooms.items() if z != 1.0]
    if zoom_note:
        lines.append(
            "- 本次未做 ¹⁸O 标记，%s 通道纵轴临时放粗 %g 倍，"
            "只用来看背景稳定性；做标记实验时把 config.yaml 里的 "
            "`zoom` 改回 1.0。"
            % ("、".join("m/z %d" % mz for mz in zoom_note),
               zooms[zoom_note[0]]))
    lines.append("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
