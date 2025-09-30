#!/usr/bin/env python3
"""
Plot script for Lab 2 results
- Reads flows.jsonl and stats.csv
- Generates three plots:
  1. CDF of FCT (WebSearch + DataMining)
  2. Mean FCT vs Intensity
  3. 95th/99th percentile FCT vs Intensity
"""

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# -------------------------------
# Load data
# -------------------------------
def load_flows(path="flows.jsonl"):
    records = []
    with open(path, "r") as f:
        for line in f:
            records.append(json.loads(line))
    return pd.DataFrame(records)

def load_stats(path="stats.csv"):
    return pd.read_csv(path)

# -------------------------------
# Plot 1: CDF of FCT
# -------------------------------
def plot_cdf(df, traffic_type, savefile=None):
    type_map = {1: "WebSearch", 2: "DataMining"}
    subset = df[df["traffic_type"] == traffic_type]

    plt.figure(figsize=(8, 5))
    for inten, group in subset.groupby("intensity"):
        vals = np.sort(group["fct_s"].values)
        y = np.arange(1, len(vals) + 1) / len(vals)
        plt.plot(vals, y, label=f"{inten} flows/s")

    plt.xlabel("Flow Completion Time (s)")
    plt.ylabel("CDF")
    plt.title(f"CDF of FCT – {type_map[traffic_type]}")
    plt.grid(True)
    plt.legend(title="Intensity")

    if savefile:
        plt.savefig(savefile)
        print(f"[Saved] {savefile}")
    else:
        plt.show()

# -------------------------------
# Plot 2: Mean FCT vs Intensity
# -------------------------------
def plot_mean(stats_df, savefile=None):
    plt.figure(figsize=(8, 5))
    for traffic in stats_df["traffic_type"].unique():
        subset = stats_df[stats_df["traffic_type"] == traffic]
        plt.plot(subset["intensity"], subset["mean_fct"], marker="o", label=traffic)

    plt.xlabel("Traffic Intensity (flows/s)")
    plt.ylabel("Mean FCT (s)")
    plt.title("Mean Flow Completion Time")
    plt.grid(True)
    plt.legend()

    if savefile:
        plt.savefig(savefile)
        print(f"[Saved] {savefile}")
    else:
        plt.show()

# -------------------------------
# Plot 3: Percentiles vs Intensity
# -------------------------------
def plot_percentiles(stats_df, savefile=None):
    plt.figure(figsize=(8, 5))
    for traffic in stats_df["traffic_type"].unique():
        subset = stats_df[stats_df["traffic_type"] == traffic]
        plt.plot(subset["intensity"], subset["p95_fct"], marker="s", label=f"{traffic} – 95th pct")
        plt.plot(subset["intensity"], subset["p99_fct"], marker="^", label=f"{traffic} – 99th pct")

    plt.xlabel("Traffic Intensity (flows/s)")
    plt.ylabel("FCT (s)")
    plt.title("95th and 99th Percentile Flow Completion Times")
    plt.grid(True)
    plt.legend()

    if savefile:
        plt.savefig(savefile)
        print(f"[Saved] {savefile}")
    else:
        plt.show()

# -------------------------------
# Main
# -------------------------------
def main():
    flows_df = load_flows("flows.jsonl")
    stats_df = load_stats("stats.csv")

    # Plot 1 – CDFs
    plot_cdf(flows_df, 1, "cdf_websearch.png")
    plot_cdf(flows_df, 2, "cdf_datamining.png")

    # Plot 2 – Mean
    plot_mean(stats_df, "mean_fct.png")

    # Plot 3 – Percentiles
    plot_percentiles(stats_df, "percentiles_fct.png")

if __name__ == "__main__":
    main()
