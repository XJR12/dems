#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEMS 三通道 Cycle 图绘制。

版式（照师姐原图）：
  每个样品一张图，自上而下三层独立框、零间距紧贴：m/z 36 / 34 / 32；
  三格共享同一条横轴，只有最底层标 1–5 与 Cycle，上两层只留小刻度；
  每层左上角是“数值 + 紧跟的工字形比例尺”，右上角是彩色 m/z 标签；
  曲线颜色向下渐变成白色，一直填到该层底边。

配色、字号、缩放、留白全部读 config.yaml。
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgb
from matplotlib.ticker import MultipleLocator


def setup_rc(cfg):
    font = cfg["figure"].get("font", "Arial")
    plt.rcParams["font.family"] = font
    plt.rcParams["mathtext.fontset"] = "custom"
    plt.rcParams["mathtext.rm"] = font
    plt.rcParams["mathtext.bf"] = font + ":bold"
    plt.rcParams["mathtext.it"] = font + ":italic"
    plt.rcParams["mathtext.default"] = "regular"
    plt.rcParams["axes.unicode_minus"] = False


def gradient_fill(ax, x, y, color, ymin, ymax, x0, x1):
    """曲线颜色 → 白色，自上而下渐变，填到该层底边。

    渐变顶端跟着这条曲线自己的最高点走，所以多个样品共用同一段比例尺时，
    曲线矮的样品也是峰尖处最白，不会出现上方一片空白渐变。
    """
    poly = ax.fill_between(x, ymin, y, color="none", linewidth=0)
    path = poly.get_paths()[0]
    rgb = np.array(to_rgb(color))
    n = 256
    t = np.linspace(0.0, 1.0, n)[:, None, None]
    grad_rgb = (1.0 - t) + t * rgb.reshape(1, 1, 3)
    grad = np.concatenate([grad_rgb, np.ones((n, 1, 1))], axis=2)
    y_full = float(np.nanmax(y))
    if not np.isfinite(y_full) or y_full <= ymin:
        y_full = ymin + 1e-6 * (ymax - ymin)
    im = ax.imshow(grad, extent=[x0, x1, ymin, y_full], aspect="auto",
                   origin="lower", interpolation="bilinear", zorder=1)
    im.set_clip_path(path, transform=ax.transData)


def draw_scale_bar(ax, label, bar_frac, y_top, cfg):
    sb = cfg["scale_bar"]
    txt = ax.text(float(sb["left"]), y_top, label, transform=ax.transAxes,
                  ha="left", va="top", fontsize=float(sb["text_size"]),
                  fontweight="bold")
    fig = ax.figure
    fig.canvas.draw()
    bb = txt.get_window_extent(renderer=fig.canvas.get_renderer())
    inv = ax.transAxes.inverted()
    x_mid = inv.transform((bb.x1, bb.y0))[0] + 0.012

    y_bot = max(0.02, y_top - bar_frac)
    cap = 0.010
    ax.plot([x_mid, x_mid], [y_bot, y_top], transform=ax.transAxes,
            color="black", linewidth=1.0, clip_on=False)
    ax.plot([x_mid - cap, x_mid + cap], [y_top, y_top], transform=ax.transAxes,
            color="black", linewidth=1.0, clip_on=False)
    ax.plot([x_mid - cap, x_mid + cap], [y_bot, y_bot], transform=ax.transAxes,
            color="black", linewidth=1.0, clip_on=False)


def draw_box(ax, x, y, channel, ylim, bar, cfg, show_numbers, nticks):
    layout = cfg["layout"]
    color = channel["color"]
    species = channel["label"]

    decimals = int(cfg["scale_bar"]["decimals"])
    bar_text = r"$\mathbf{%.*f\times10^{%d}}$" % (
        decimals, bar["mant"], bar["exp"])

    ymin, ymax = ylim
    x_pad = float(layout["x_pad"]) * (x.max() - x.min())
    x0, x1 = x.min() - x_pad, x.max() + x_pad

    gradient_fill(ax, x, y, color, ymin, ymax, x0, x1)

    ax.plot(x, y, color=color, linewidth=1.3, solid_joinstyle="round",
            solid_capstyle="round", zorder=3)

    for spine in ax.spines.values():
        spine.set_linewidth(1.2)
        spine.set_color("black")
    ax.set_xlim(x0, x1)
    ax.set_ylim(ymin, ymax)
    ax.set_yticks([])
    ax.set_xticks(list(range(1, nticks + 1)))
    ax.xaxis.set_major_locator(MultipleLocator(1.0))
    ax.tick_params(axis="x", direction="out", length=3.0, width=1.0,
                   labelsize=7.0, pad=2.5, labelbottom=show_numbers)
    ax.tick_params(axis="y", length=0)

    sb = cfg["scale_bar"]
    draw_scale_bar(ax, bar_text, float(sb["height"]),
                   float(sb["text_top"]), cfg)

    ax.text(float(sb["right"]), 0.975, species, transform=ax.transAxes,
            ha="right", va="top", fontsize=float(sb["text_size"]),
            fontweight="bold", color=color)


def plot_sample(record, cfg, out_path):
    setup_rc(cfg)
    fig_cfg = cfg["figure"]
    layout = cfg["layout"]
    fig = plt.figure(figsize=tuple(fig_cfg["figsize"]),
                     dpi=int(fig_cfg["dpi"]), facecolor="white")
    gs = fig.add_gridspec(
        len(cfg["channels"]), 1,
        left=float(layout["left"]), right=float(layout["right"]),
        top=float(layout["top"]), bottom=float(layout["bottom"]),
        hspace=float(layout["hspace"]))

    channels = cfg["channels"]
    nticks = int(record["n_used"])
    for row, channel in enumerate(channels):
        mz = int(channel["mz"])
        ax = fig.add_subplot(gs[row, 0])
        draw_box(ax, record["x"], record["vals"][mz], channel,
                 record["stats"][mz]["ylim"], record["bars"][mz],
                 cfg, show_numbers=(row == len(channels) - 1), nticks=nticks)
        if row == (len(channels) - 1) // 2:
            ax.set_ylabel(cfg["text"]["ylabel"], fontsize=9.5,
                          fontweight="bold", labelpad=5)
        if row == len(channels) - 1:
            ax.set_xlabel(cfg["text"]["xlabel"], fontsize=9.5,
                          fontweight="bold", labelpad=4)

    fig.savefig(out_path, dpi=int(fig_cfg["dpi"]), bbox_inches="tight",
                pad_inches=float(fig_cfg["pad_inches"]), facecolor="white")
    plt.close(fig)
    return out_path
