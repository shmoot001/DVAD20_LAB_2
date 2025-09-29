#!/usr/bin/env python3
"""
Plotting Script for Data Center Traffic Simulation
--------------------------------------------------
Reads flow logs from JSONL or CSV and generates graphs.
Saves plots to PNG files instead of displaying them.
"""

import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
# ----------------------------
# Load flows from JSONL
# ----------------------------
def load_flows(log_file: str = "flows.jsonl") -> pd.DataFrame:
    records = []
    with open(log_file, "r") as f:
        for line in f:
            records.append(json.loads(line))
    return pd.DataFrame(records)

# ----------------------------
# Compute statistics
# ----------------------------
def compute_statistics(df: pd.DataFrame) -> pd.DataFrame:
    stats = []
    for (traffic_type, intensity), group in df.groupby(["traffic_type", "intensity"]):
        fcts = group["fct_s"].values
        stats.append({
            "traffic_type": traffic_type,
            "intensity": intensity,
            "mean_fct": np.mean(fcts),
            "p95_fct": np.percentile(fcts, 95),
            "p99_fct": np.percentile(fcts, 99)
        })
    return pd.DataFrame(stats)

# ----------------------------
# Plot mean / p95 / p99
# ----------------------------
def plot_statistics(stats_df: pd.DataFrame, title_prefix: str = "", outdir: str = "plots"):
    os.makedirs(outdir, exist_ok=True)  # make sure folder exists
    type_map = {1: "Web Search", 2: "Data Mining"}
    stats_df["Traffic"] = stats_df["traffic_type"].map(type_map)

    for traffic in ["Web Search", "Data Mining"]:
        subset = stats_df[stats_df["Traffic"] == traffic]

        plt.figure(figsize=(8, 5))
        plt.plot(subset["intensity"].to_numpy(), subset["mean_fct"].to_numpy(),
                 marker="o", label="Mean FCT")
        plt.plot(subset["intensity"].to_numpy(), subset["p95_fct"].to_numpy(),
                 marker="s", label="95th percentile FCT")
        plt.plot(subset["intensity"].to_numpy(), subset["p99_fct"].to_numpy(),
                 marker="^", label="99th percentile FCT")

        plt.xlabel("Traffic Intensity (flows/sec)")
        plt.ylabel("Flow Completion Time (seconds)")
        plt.title(f"{title_prefix}{traffic} Traffic")
        plt.grid(True)
        plt.legend()
        plt.tight_layout()

        # Save to file
        filename = os.path.join(outdir, f"{traffic.replace(' ', '_').lower()}_stats.png")
        plt.savefig(filename)
        plt.close()
        print(f"Saved: {filename}")


# ----------------------------
# Plot Boxplots (FCT per Intensity)
# ----------------------------


def plot_boxplot_broken(df: pd.DataFrame, traffic_type: int,
                        title_prefix: str = "", outdir: str = "plots",
                        low_percentile: float = 95, high_percentile: float = 99,
                        headroom: float = 0.1):
    """
    Två staplade axlar (bruten y-axel):
      - Övre: zoom till 0..(low_percentile) med lite marginal
      - Nedre: visar svansen från (high_percentile)..max  => alla outliers syns
    Sparar: <web_search|data_mining>_boxplot_broken.png
    """
    os.makedirs(outdir, exist_ok=True)
    type_map = {1: "Web Search", 2: "Data Mining"}
    name = type_map[traffic_type]

    sub = df[df["traffic_type"] == traffic_type]
    if sub.empty:
        print(f"No data for {name}; skipping.")
        return

    intensities = sorted(sub["intensity"].unique())
    data = [sub[sub["intensity"] == i]["fct_s"].values for i in intensities]

    # Beräkna intervall
    y_low_max   = np.percentile(sub["fct_s"], low_percentile)
    y_high_min  = np.percentile(sub["fct_s"], high_percentile)
    y_high_max  = sub["fct_s"].max()

    fig, (ax_top, ax_bottom) = plt.subplots(
        2, 1, sharex=True, figsize=(8, 6),
        gridspec_kw={"height_ratios": [3, 1]}
    )

    # Övre (zoomad)
    ax_top.boxplot(data, positions=range(1, len(data)+1), showfliers=True,
                   patch_artist=True, boxprops=dict(facecolor="skyblue"))
    ax_top.set_ylim(0, y_low_max * (1 + headroom))
    ax_top.set_ylabel("Flow Completion Time (s)")
    ax_top.set_title(f"{title_prefix}{name}")

    # Nedre (svansen / outliers)
    ax_bottom.boxplot(data, positions=range(1, len(data)+1), showfliers=True,
                      patch_artist=True, boxprops=dict(facecolor="skyblue"))
    ax_bottom.set_ylim(y_high_min, y_high_max * (1 + headroom))
    ax_bottom.set_xlabel("Traffic Intensity (flows/s)")
    ax_bottom.set_ylabel("Tail (s)")

    # X-ticks
    for ax in (ax_top, ax_bottom):
        ax.set_xticks(range(1, len(data)+1))
        ax.set_xticklabels(intensities)

    # ”Break”-markeringar
    d = .008
    kwargs = dict(color='k', clip_on=False)
    ax_top.plot((-d, +d), (-d, +d), transform=ax_top.transAxes, **kwargs)
    ax_top.plot((1-d, 1+d), (-d, +d), transform=ax_top.transAxes, **kwargs)
    ax_bottom.plot((-d, +d), (1-d, 1+d), transform=ax_bottom.transAxes, **kwargs)
    ax_bottom.plot((1-d, 1+d), (1-d, 1+d), transform=ax_bottom.transAxes, **kwargs)

    plt.tight_layout()
    out = os.path.join(outdir, f"{name.replace(' ', '_').lower()}_boxplot_broken.png")
    plt.savefig(out)
    plt.close()
    print(f"Saved: {out}")

def plot_boxplots(df: pd.DataFrame, title_prefix: str = "", outdir: str = "plots"):
    plot_boxplot_broken(df, 1, title_prefix, outdir)  # Web Search
    plot_boxplot_broken(df, 2, title_prefix, outdir)  # Data Mining


# ----------------------------
# Plot CDF
# ----------------------------
def plot_cdf(df: pd.DataFrame, traffic_type: int, title_prefix: str = "", outdir: str = "plots"):
    os.makedirs(outdir, exist_ok=True)
    type_map = {1: "Web Search", 2: "Data Mining"}
    traffic_name = type_map[traffic_type]

    subset = df[df["traffic_type"] == traffic_type]

    plt.figure(figsize=(8, 5))
    for intensity, group in subset.groupby("intensity"):
        fcts = np.sort(group["fct_s"].values)
        y = np.arange(1, len(fcts) + 1) / len(fcts)
        plt.plot(fcts, y, label=f"{intensity} flows/sec")

    plt.xlabel("Flow Completion Time (seconds)")
    plt.ylabel("CDF")
    plt.title(f"{title_prefix}{traffic_name} Traffic - CDF of FCT")
    plt.grid(True)
    plt.legend(title="Intensity")
    plt.tight_layout()

    # Save to file
    filename = os.path.join(outdir, f"{traffic_name.replace(' ', '_').lower()}_cdf.png")
    plt.savefig(filename)
    plt.close()
    print(f"Saved: {filename}")

# ----------------------------
# Main
# ----------------------------
def main():
    df = load_flows("flows.jsonl")
    stats_df = compute_statistics(df)

    # Save plots
    plot_statistics(stats_df, title_prefix="Baseline (20 Mbps) - ")
    plot_cdf(df, traffic_type=1, title_prefix="Baseline (20 Mbps) - ")
    plot_cdf(df, traffic_type=2, title_prefix="Baseline (20 Mbps) - ")
    plot_boxplots(df, title_prefix="Baseline (20 Mbps) - ")

if __name__ == "__main__":
    main()
