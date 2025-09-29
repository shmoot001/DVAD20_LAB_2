#!/usr/bin/env python3
"""
Experiment script for Practical Assignment #2 (Basic Track)
- Builds one-pod fat-tree topo
- Runs WebSearch & DataMining flows
- Logs Flow Completion Times (FCT)
- Saves statistics + graphs
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
# One-Pod Fat-Tree Topology
# -------------------------------
class OnePodFatTree(Topo):
    def build(self):
        h1, h2, h3, h4 = [self.addHost(f'h{i}') for i in range(1, 5)]
        s1, s2, s3, s4 = [self.addSwitch(f's{i}') for i in range(1, 5)]
        opts = dict(bw=20, delay='1ms', use_htb=True)

        self.addLink(h1, s1, **opts); self.addLink(h2, s1, **opts)
        self.addLink(h3, s3, **opts); self.addLink(h4, s3, **opts)
        self.addLink(s1, s2, **opts); self.addLink(s1, s4, **opts)
        self.addLink(s3, s2, **opts); self.addLink(s3, s4, **opts)
        print("[Topo] One-Pod Fat-Tree built")

# -------------------------------
# Traffic generation
# -------------------------------
WEBSEARCH_ECDF = [(10_000,0.10),(20_000,0.30),(35_000,0.60),
                  (50_000,0.90),(80_000,0.95),(100_000,1.0)]

DATAMINING_ECDF = [(200,0.10),(300,0.20),(450,0.30),
                   (570,0.40),(600,0.60),(650,0.70),
                   (700,0.80),(900,1.0)]

def sample_from_ecdf(ecdf):
    r = random.random()
    for value, prob in ecdf:
        if r <= prob: return value
    return ecdf[-1][0]

def get_sampler(t): 
    return (lambda: sample_from_ecdf(WEBSEARCH_ECDF)) if t==1 else (lambda: sample_from_ecdf(DATAMINING_ECDF))

def genDCTraffic(src, dst, traffic_type, intensity, duration, port=5001, on_done=None):
    sampler = get_sampler(traffic_type)
    fcts = []
    recv = dst.popen(f"iperf -s -p {port} > /dev/null 2>&1", shell=True)
    time.sleep(0.3)
    t0, next_tick, seq = time.time(), time.time(), 0
    in_flight, meta = {}, {}
    try:
        while (time.time()-t0) < duration or in_flight:
            now = time.time()
            if now >= next_tick and (now-t0) < duration:
                for _ in range(intensity):
                    seq += 1
                    size_b = sampler()
                    start_ts = time.time()
                    cmd = f"iperf -c {dst.IP()} -p {port} -n {size_b} > /dev/null 2>&1"
                    proc = src.popen(cmd, shell=True)
                    in_flight[seq], meta[seq] = proc, {"start_ts": start_ts, "size": size_b}
                next_tick += 1
            for fid, proc in list(in_flight.items()):
                if proc.poll() is not None:
                    end = time.time(); info = meta[fid]
                    fct = end-info["start_ts"]; fcts.append(fct)
                    if on_done: on_done({"src":src.name,"dst":dst.name,
                        "traffic_type":traffic_type,"intensity":intensity,
                        "size_bytes":info["size"],"fct_s":fct})
                    del in_flight[fid], meta[fid]
            time.sleep(0.01)
    finally: recv.terminate()
    return fcts

# -------------------------------
# Experiment runner
# -------------------------------
class FlowLogger:
    def __init__(self, path="flows.jsonl"): self.path=path
    def write(self, rec): open(self.path,"a").write(json.dumps(rec)+"\n")

class Experiment:
    def __init__(self, net): self.net=net; self.logger=FlowLogger()
    def _on_done(self, rec): self.logger.write(rec)
    def run(self, times=10, intensity=10, duration=10):
        hosts=[self.net.get(f"h{i}") for i in range(1,5)]
        for rep in range(times):
            src,dst=random.sample(hosts,2)
            print(f"[Experiment] Rep {rep+1}/{times}, src={src.name}, dst={dst.name}")
            for t in (1,2):
                print(f"[Experiment] Traffic type={'WebSearch' if t==1 else 'DataMining'}")
                for bulk in range(1,intensity+1):
                    print(f"[Experiment] Intensity {bulk}/{intensity}")
                    genDCTraffic(src,dst,t,bulk,duration,on_done=self._on_done)

# -------------------------------
# Analysis
# -------------------------------
def load_flows(path="flows.jsonl"): 
    return pd.DataFrame([json.loads(l) for l in open(path)])

def compute_statistics(df):
    rows=[]
    for (t,inten),group in df.groupby(["traffic_type","intensity"]):
        fcts=group["fct_s"].values
        rows.append({
            "traffic_type": "WebSearch" if t==1 else "DataMining",
            "intensity": inten,
            "mean_fct": np.mean(fcts),
            "p95_fct": np.percentile(fcts,95),
            "p99_fct": np.percentile(fcts,99)
        })
    return pd.DataFrame(rows)

def plot_cdf(df, t, title="", savefile=None):
    subset=df[df["traffic_type"]==t]; plt.figure()
    for inten, group in subset.groupby("intensity"):
        vals=np.sort(group["fct_s"].values); y=np.arange(1,len(vals)+1)/len(vals)
        plt.plot(vals,y,label=f"{inten} flows/s")
    plt.xlabel("Flow Completion Time (s)"); plt.ylabel("CDF")
    plt.title(title + ("WebSearch" if t==1 else "DataMining")); plt.grid(); plt.legend()
    if savefile: 
        plt.savefig(savefile)
        print(f"[Saved] {savefile}")
    plt.close()

# -------------------------------
# Main
# -------------------------------
def main():
    setLogLevel("info")
    topo=OnePodFatTree()
    net=Mininet(topo=topo,link=TCLink,switch=OVSSwitch,controller=None,autoSetMacs=True)
    net.addController("c0",controller=RemoteController,ip="127.0.0.1",port=6633)
    net.start()
    try:
        exp=Experiment(net); exp.run(times=10,intensity=10,duration=10)
        df=load_flows()
        stats=compute_statistics(df)
        stats.to_csv("stats.csv",index=False)
        print("[Saved] stats.csv")

        plot_cdf(df,1,"Round Robin - ","cdf_websearch.png")
        plot_cdf(df,2,"Round Robin - ","cdf_datamining.png")
    finally: net.stop()

if __name__=="__main__": main()
