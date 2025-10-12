#!/usr/bin/env python3
"""
Lab 2 Experiment Script
-----------------------
Creates a one-pod fat-tree topology (4 hosts, 4 switches)
and generates WebSearch & DataMining traffic using iperf.
Uses static ARP, logs Flow Completion Times (FCT),
and produces plots and summary statistics.
"""

import os, json, time, random
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from mininet.link import TCLink
from mininet.log import setLogLevel

# -------------------------------
# Topology
# -------------------------------
class OnePodFatTree(Topo):
    def build(self):
        h1, h2, h3, h4 = [self.addHost(f'h{i}') for i in range(1, 5)]
        s1, s2, s3, s4 = [self.addSwitch(f's{i}') for i in range(1, 5)]
        opts = dict(bw=20, delay='1ms', use_htb=True)
        self.addLink(h1, s1, **opts)
        self.addLink(h2, s1, **opts)
        self.addLink(h3, s3, **opts)
        self.addLink(h4, s3, **opts)
        self.addLink(s1, s2, **opts)
        self.addLink(s1, s4, **opts)
        self.addLink(s3, s2, **opts)
        self.addLink(s3, s4, **opts)
        print("[TOPO] One-Pod FatTree built successfully")

# -------------------------------
# ECDF distributions
# -------------------------------
WEBSEARCH_ECDF = [(10_000,0.10),(20_000,0.30),(35_000,0.60),
                  (50_000,0.90),(80_000,0.95),(100_000,1.0)]
DATAMINING_ECDF = [
    (50_000,      0.10),  # 50 KB    → 10% of flows are ≤ 50 KB
    (100_000,     0.20),  # 100 KB   → 20% of flows are ≤ 100 KB
    (250_000,     0.30),  # 250 KB   → 30% of flows are ≤ 250 KB
    (500_000,     0.40),  # 500 KB   → 40% of flows are ≤ 500 KB
    (1_000_000,   0.60),  # 1 MB     → 60% of flows are ≤ 1 MB
    (2_000_000,   0.70),  # 2 MB     → 70% of flows are ≤ 2 MB
    (5_000_000,   0.80),  # 5 MB     → 80% of flows are ≤ 5 MB
    (10_000_000,  1.00),  # 10 MB    → 100% of flows are ≤ 10 MB (max)
]

def sample_from_ecdf(ecdf):
    r = random.random()
    for v, p in ecdf:
        if r <= p:
            return v
    return ecdf[-1][0]

def get_sampler(t):
    return (lambda: sample_from_ecdf(WEBSEARCH_ECDF)) if t==1 else (lambda: sample_from_ecdf(DATAMINING_ECDF))

# -------------------------------
# Traffic generator
# -------------------------------
def genDCTraffic(src, dst, traffic_type, intensity, duration, port=5001, on_done=None):
    sampler = get_sampler(traffic_type)
    recv = dst.popen(f"iperf -s -p {port} > /dev/null 2>&1", shell=True)
    time.sleep(0.3)
    in_flight, meta, seq, fcts = {}, {}, 0, []
    t0, next_tick = time.time(), time.time()

    try:
        while (time.time() - t0) < duration or in_flight:
            now = time.time()
            # Launch new flows per second
            if now >= next_tick and (now - t0) < duration:
                for _ in range(intensity):
                    seq += 1
                    size_b = sampler()
                    start = time.time()
                    cmd = f"iperf -c {dst.IP()} -p {port} -n {size_b} > /dev/null 2>&1"
                    proc = src.popen(cmd, shell=True)
                    in_flight[seq] = proc
                    meta[seq] = {"start": start, "size": size_b}
                next_tick += 1
            # Check completions
            for fid, proc in list(in_flight.items()):
                if proc.poll() is not None:
                    end = time.time()
                    fct = end - meta[fid]["start"]
                    fcts.append(fct)
                    record = {"src": src.name, "dst": dst.name,
                              "traffic_type": traffic_type,
                              "intensity": intensity,
                              "size_bytes": meta[fid]["size"],
                              "fct_s": fct}
                    if on_done:
                        on_done(record)
                    del in_flight[fid], meta[fid]
            time.sleep(0.01)
    finally:
        recv.terminate()
    return fcts

# -------------------------------
# Experiment runner
# -------------------------------
class FlowLogger:
    def __init__(self, path="flows.jsonl"):
        self.path = path
        if os.path.exists(path):
            os.remove(path)
    def write(self, record):
        with open(self.path, "a") as f:
            f.write(json.dumps(record) + "\n")

class Experiment:
    def __init__(self, net):
        self.net = net
        self.logger = FlowLogger()
    def _on_done(self, rec):
        print(f"[Flow] {rec}")
        self.logger.write(rec)
    def run(self, times=10, intensity=10, duration=10):
        hosts = [self.net.get(f"h{i}") for i in range(1, 5)]
        for rep in range(times):
            src, dst = random.sample(hosts, 2)
            print(f"\n[Run {rep+1}/{times}] {src.name} → {dst.name}")
            for t in (1, 2):
                label = "WebSearch" if t==1 else "DataMining"
                print(f"  Type={label}")
                for bulk in range(1, intensity+1):
                    print(f"    Intensity {bulk}/{intensity}")
                    genDCTraffic(src, dst, t, bulk, duration, on_done=self._on_done)

# -------------------------------
# Stats and plotting
# -------------------------------
def compute_stats(df):
    rows = []
    for (t, i), g in df.groupby(["traffic_type", "intensity"]):
        fcts = g["fct_s"].values
        rows.append({
            "traffic_type": "WebSearch" if t==1 else "DataMining",
            "intensity": i,
            "mean_fct": np.mean(fcts),
            "p95_fct": np.percentile(fcts, 95),
            "p99_fct": np.percentile(fcts, 99)
        })
    return pd.DataFrame(rows)

def plot_cdf(df):
    for t, name in [(1, "WebSearch"), (2, "DataMining")]:
        subset = df[df["traffic_type"]==t]
        plt.figure(figsize=(8,5))
        for inten, group in subset.groupby("intensity"):
            vals = np.sort(group["fct_s"].values)
            y = np.arange(1, len(vals)+1)/len(vals)
            plt.plot(vals, y, label=f"{inten} flows/s")
        plt.xlabel("Flow Completion Time (s)")
        plt.ylabel("CDF")
        plt.title(f"CDF of FCT – {name}")
        plt.grid(True)
        plt.legend()
        plt.savefig(f"cdf_{name.lower()}.png")

# -------------------------------
# Main
# -------------------------------
def main():
    setLogLevel("info")
    topo = OnePodFatTree()
    net = Mininet(topo=topo, link=TCLink, switch=OVSSwitch,
                  controller=None, autoSetMacs=True)
    net.addController("c0", controller=RemoteController,
                      ip="127.0.0.1", port=6633)
    net.start()
    net.staticArp()
    print("[NET] Static ARP tables configured.")

    try:
        exp = Experiment(net)
        exp.run(times=10, intensity=10, duration=10)

        df = pd.DataFrame([json.loads(l) for l in open("flows.jsonl")])
        stats = compute_stats(df)
        stats.to_csv("stats.csv", index=False)
        plot_cdf(df)
        print("[RESULT] stats.csv and CDF plots generated.")
    finally:
        net.stop()
        print("[NET] Stopped.")

if __name__ == "__main__":
    main()
