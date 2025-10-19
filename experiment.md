# 🧩 Topo

```python
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
```

---

# 🧠 Vad är det här?

Den här klassen definierar en **Mininet-topologi** — alltså den virtuella nätverksstruktur som ditt experiment bygger upp.
Den efterliknar en **1-pod Fat-Tree-topologi**, vilket är en vanlig design i datacenter.

I den här miniversionen har du:

* **4 hosts** (h1–h4)
* **4 switchar** (s1–s4)
* Länkar mellan dem med definierad **bandbredd (bw)** och **fördröjning (delay)**

---

# 🔹 1️⃣ Klassdefinition

```python
class OnePodFatTree(Topo):
```

* Klassen `OnePodFatTree` **ärver från `Topo`**, som kommer från Mininet-biblioteket.
* `Topo` används för att skapa anpassade nätverk med hosts, switchar och länkar.
* Genom att ärva från `Topo` kan du bygga din egen topologi genom att implementera metoden `build()`.

🧠 Det betyder: när du skapar `topo = OnePodFatTree()`, så anropas automatiskt funktionen `build()` för att bygga nätet.

---

# 🔹 2️⃣ build()-metoden

```python
def build(self):
```

Detta är “ritningen” för nätverket.
Allt som läggs till här (hosts, switchar, länkar) kommer att finnas i Mininet-nätverket när det startas.

---

# 🔹 3️⃣ Skapa hosts

```python
h1, h2, h3, h4 = [self.addHost(f'h{i}') for i in range(1, 5)]
```

* `self.addHost()` lägger till en host i topologin.
* Loopen `[self.addHost(f'h{i}') for i in range(1, 5)]` skapar fyra hosts med namnen `h1`, `h2`, `h3`, `h4`.
* Dessa representerar **slutanvändare eller servrar** i nätet.

🧠 I Mininet får varje host:

* ett eget virtuellt nätverksinterface,
* en egen IP-adress (t.ex. `10.0.0.1`),
* och kan köra kommandon (t.ex. `ping`, `iperf`, etc.).

---

# 🔹 4️⃣ Skapa switchar

```python
s1, s2, s3, s4 = [self.addSwitch(f's{i}') for i in range(1, 5)]
```

* `self.addSwitch()` lägger till en OpenFlow-switch i nätverket.
* Du får fyra switchar: `s1`, `s2`, `s3`, `s4`.
* Dessa kopplas senare ihop med länkar (se nedan).
* Alla dessa switchar kommer att kopplas till din Ryu-controller när nätet startas.

🧠 DPID (datapath ID) för dessa switchar sätts automatiskt baserat på namnet:
`s1 → DPID=1`, `s2 → DPID=2`, osv.

---

# 🔹 5️⃣ Definiera länkegenskaper

```python
opts = dict(bw=20, delay='1ms', use_htb=True)
```

Här definieras standardegenskaper för varje länk:

* **bw=20** → Bandwidth = 20 Mbps
* **delay='1ms'** → Länkfördröjning = 1 millisekund
* **use_htb=True** → Använd Linux HTB (Hierarchical Token Bucket) för att kontrollera bandbredd.

💡 Detta simulerar realistiska nätverksförhållanden i datacenter (snabba men inte perfekta länkar).

---

# 🔹 6️⃣ Lägg till länkar (hosts ↔ switchar)

```python
self.addLink(h1, s1, **opts)
self.addLink(h2, s1, **opts)
self.addLink(h3, s3, **opts)
self.addLink(h4, s3, **opts)
```

* Kopplar hosts till sina edge-switchar:

  * h1 och h2 kopplas till s1
  * h3 och h4 kopplas till s3

🧠 Det betyder att:

* s1 fungerar som **edge-switch** för h1 och h2.
* s3 fungerar som **edge-switch** för h3 och h4.

---

# 🔹 7️⃣ Lägg till länkar (switchar ↔ aggregering)

```python
self.addLink(s1, s2, **opts)
self.addLink(s1, s4, **opts)
self.addLink(s3, s2, **opts)
self.addLink(s3, s4, **opts)
```

Detta skapar kärnan i din **Fat-Tree-struktur**:

* s1 och s3 (edge-switchar) kopplas upp till **s2 och s4 (aggregation-switchar)**
* Det blir **fyra länkar totalt** mellan edge och aggregation.

🧠 Resultatet är en symmetrisk struktur — två vägar mellan varje hostpar.
Round Robin i din Ryu-controller kommer att använda dessa uplinks (port 1 och 2) på s2/s4 för att fördela trafiken.

---

# 🔹 8️⃣ Utskrift (för loggning)

```python
print("[TOPO] One-Pod FatTree built successfully")
```

* Skriver ut ett bekräftelsemeddelande i terminalen när topologin skapats.
* Hjälper dig att se att nätverket byggts utan fel.

---

# 🔹 9️⃣ Resultat: topologin (visuellt)

```
          s2           s4
         /  \         /  \
       s1----\-------/----s3
      /  \             /  \
    h1   h2          h3   h4
```

* s1 & s3 = edge-switchar (kopplade till hosts)
* s2 & s4 = aggregation-switchar (kopplade till edges via uplinks)
* Round Robin-logiken balanserar trafiken mellan vägar via s2 och s4.

---

# 🔹 Sammanfattning i punktform

| Del             | Vad den gör                                               |
| --------------- | --------------------------------------------------------- |
| **addHost()**   | Skapar hosts (h1–h4).                                     |
| **addSwitch()** | Skapar switchar (s1–s4).                                  |
| **opts**        | Definierar länkegenskaper (bandbredd, delay).             |
| **addLink()**   | Kopplar ihop hosts och switchar enligt Fat-Tree-struktur. |
| **print()**     | Bekräftar att topologin är byggd.                         |

---

# 💡 Kortfattat

> `OnePodFatTree` skapar en liten men realistisk datacenter-topologi med fyra switchar och fyra hosts.
> s1 och s3 fungerar som edge-switchar, s2 och s4 som aggregation-switchar.
> Trafik från hosts skickas uppåt till aggregation-nivån, där din Ryu-controller använder **Round Robin** för att jämnt fördela trafiken mellan de två uplinks.




# 🧩 ECDFc

```python
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
```

---

# 🧠 Vad betyder det här?

Här definieras två **empiriska fördelningar (eCDFs)** — en för WebSearch och en för DataMining.
De används för att **simulera olika typer av nätverkstrafik** med realistiska variationer i flödesstorlek (dvs. hur mycket data som skickas per “flow”).

💡 eCDF = *empirical cumulative distribution function*
Det betyder: “för varje flödesstorlek, hur stor andel (%) av alla flöden är mindre än eller lika stora som detta värde?”

---

# 🔹 1️⃣ WEBSEARCH_ECDF

```python
WEBSEARCH_ECDF = [
    (10_000, 0.10),
    (20_000, 0.30),
    (35_000, 0.60),
    (50_000, 0.90),
    (80_000, 0.95),
    (100_000, 1.0)
]
```

* Denna lista representerar WebSearch-trafik, som typiskt består av **många små flöden** (t.ex. webbfrågor, API-anrop).
* Formatet är `(storlek_i_bytes, sannolikhet)`.

| Flow Size (bytes) | Cumulative Probability | Förklaring                              |
| ----------------- | ---------------------- | --------------------------------------- |
| 10 000            | 0.10                   | 10% av alla WebSearch-flöden är ≤ 10 KB |
| 20 000            | 0.30                   | 30% är ≤ 20 KB                          |
| 35 000            | 0.60                   | 60% är ≤ 35 KB                          |
| 50 000            | 0.90                   | 90% är ≤ 50 KB                          |
| 80 000            | 0.95                   | 95% är ≤ 80 KB                          |
| 100 000           | 1.00                   | 100% är ≤ 100 KB (ingen större)         |

💡 **Tolkning:** WebSearch-trafik är lätt och snabb — de flesta flöden är små, vilket ger korta FCT (Flow Completion Times).

---

# 🔹 2️⃣ DATAMINING_ECDF

```python
DATAMINING_ECDF = [
    (50_000, 0.10),
    (100_000, 0.20),
    (250_000, 0.30),
    (500_000, 0.40),
    (1_000_000, 0.60),
    (2_000_000, 0.70),
    (5_000_000, 0.80),
    (10_000_000, 1.00)
]
```

* Representerar **tyngre datacenter-trafik**, som t.ex. filöverföringar, databasreplikering eller analysjobb.
* Här är flödena mycket större (upp till 10 MB).

| Flow Size  | Cumulative Probability | Förklaring             |
| ---------- | ---------------------- | ---------------------- |
| 50 000     | 0.10                   | 10% av flödena ≤ 50 KB |
| 500 000    | 0.40                   | 40% ≤ 500 KB           |
| 1 000 000  | 0.60                   | 60% ≤ 1 MB             |
| 10 000 000 | 1.00                   | 100% ≤ 10 MB           |

💡 **Tolkning:** DataMining-flöden är längre och mer bandbreddskrävande. De belastar nätet mer och leder ofta till högre FCT.

---

# 🔹 3️⃣ sample_from_ecdf(ecdf)

```python
def sample_from_ecdf(ecdf):
    r = random.random()
    for v, p in ecdf:
        if r <= p:
            return v
    return ecdf[-1][0]
```

### 🔍 Förklaring:

1. `r = random.random()` → genererar ett slumpmässigt tal mellan 0 och 1.
   Exempel: `r = 0.37`

2. `for v, p in ecdf:` → loopar igenom alla `(storlek, sannolikhet)` i eCDF-listan.

3. `if r <= p:` → hittar första punkten där sannolikheten i eCDF är större än `r`.
   → returnerar den flödesstorleken `v`.

4. Om inget matchar (r ~ 1.0) → returnerar sista värdet (det största).

🧠 Det här motsvarar att **dra ett slumpmässigt prov från distributionen**.
→ Varje gång funktionen kallas returnerar den en **ny slumpmässig flödesstorlek** enligt sannolikheterna i eCDF.

---

# 🔹 4️⃣ get_sampler(t)

```python
def get_sampler(t):
    return (lambda: sample_from_ecdf(WEBSEARCH_ECDF)) if t==1 else (lambda: sample_from_ecdf(DATAMINING_ECDF))
```

### 🔍 Förklaring:

* `t` är en parameter som anger **vilken typ av trafik** vi vill simulera:

  * `t = 1` → WebSearch
  * `t = 2` → DataMining

Funktionen returnerar en **lambda (anonym funktion)** som du kan anropa för att få ett nytt flödesprov varje gång.

🧠 Exempel:

```python
sampler = get_sampler(2)   # 2 = DataMining
flow_size = sampler()      # Returnerar t.ex. 1_000_000 bytes (≈ 1 MB)
```

Detta gör koden enkel att använda i trafikgeneratorn senare:

```python
size_b = size_sampler()  # varje gång: ny slumpmässig storlek
```

---

# 🔹 5️⃣ Varför behövs detta?

Syftet är att simulera **verklig datacentertrafik**.
Alla flöden är inte lika stora — vissa är små (snabba API-anrop), andra är jättestora (dataanalys).

Att använda eCDF gör att simuleringen blir:

* **realistisk** (efterliknar verkliga mätdata),
* **replicerbar** (du kan återanvända samma fördelning i olika experiment),
* **kontrollerbar** (du kan jämföra olika workload-typer under samma villkor).

---

# 🔹 6️⃣ Sammanfattning

| Del                  | Vad den gör                                                                        |
| -------------------- | ---------------------------------------------------------------------------------- |
| `WEBSEARCH_ECDF`     | Beskriver sannolik fördelning av små flöden (typiska webbtjänster).                |
| `DATAMINING_ECDF`    | Beskriver sannolik fördelning av stora flöden (tunga datajobb).                    |
| `sample_from_ecdf()` | Returnerar en slumpmässig flödesstorlek baserat på eCDF.                           |
| `get_sampler(t)`     | Väljer rätt eCDF (WebSearch eller DataMining) och returnerar en generatorfunktion. |

---

# 💡 Kortfattat

> Den här delen av koden definierar hur **flödesstorlekarna slumpas fram** i simuleringen.
> Den använder empiriska CDF-fördelningar för två trafiktyper:
> **WebSearch** med små snabba flöden, och **DataMining** med större, bandbreddskrävande flöden.
>
> Genom att dra slumpmässiga prover från dessa distributioner får varje simulering en realistisk blandning av små och stora flöden — precis som i ett verkligt datacenter.



# 🧩 genDCTraffic

```python
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
```

---

# 🧠 Vad funktionen gör

Den här funktionen **skapar och mäter trafik mellan två Mininet-hostar (`src` och `dst`)**.
Den använder verktyget **iperf** för att simulera TCP-flöden och mäter **hur lång tid (Flow Completion Time, FCT)** varje flöde tar att avslutas.

Den imiterar alltså realistisk datacentertrafik med flera samtidiga små eller stora flöden, beroende på:

* `traffic_type` (WebSearch eller DataMining),
* `intensity` (antal flöden per sekund),
* `duration` (hur länge trafiken ska genereras).

---

# 🔹 1️⃣ Funktionens parametrar

| Parameter      | Typ          | Förklaring                                                         |
| -------------- | ------------ | ------------------------------------------------------------------ |
| `src`          | Mininet host | Källa (t.ex. h1) som skickar trafiken                              |
| `dst`          | Mininet host | Destination (t.ex. h4) som tar emot trafiken                       |
| `traffic_type` | int          | 1 = WebSearch, 2 = DataMining                                      |
| `intensity`    | int          | Antal nya flöden som startas varje sekund                          |
| `duration`     | int          | Hur länge nya flöden genereras (sekunder)                          |
| `port`         | int          | TCP-port som iperf använder (standard 5001)                        |
| `on_done`      | funktion     | Callback som körs när ett flöde avslutas (t.ex. loggning till fil) |

---

# 🔹 2️⃣ Välj rätt trafiksampler

```python
sampler = get_sampler(traffic_type)
```

* Hämtar rätt **eCDF-sampler** baserat på `traffic_type`.
* Det betyder att varje gång vi kallar `sampler()`, får vi **en slumpmässig flow size** enligt WebSearch- eller DataMining-fördelningen.

🧠 Exempel:

```python
size_b = sampler()   # returnerar t.ex. 50_000 bytes för WebSearch
```

---

# 🔹 3️⃣ Starta iperf-server på destinationen

```python
recv = dst.popen(f"iperf -s -p {port} > /dev/null 2>&1", shell=True)
time.sleep(0.3)
```

* Startar en **iperf-server** (`-s`) på mottagaren (`dst`).
* `> /dev/null 2>&1` tystar utmatningen (du kan ta bort det för debugging).
* `time.sleep(0.3)` ger servern en liten stund att starta upp innan klienter ansluter.

🧠 I datacentermodell:

> `dst` agerar som **server** som tar emot data från flera **klientflöden** (`src`).

---

# 🔹 4️⃣ Initiera variabler

```python
in_flight, meta, seq, fcts = {}, {}, 0, []
t0, next_tick = time.time(), time.time()
```

* `in_flight`: dict med aktiva flöden (`flow_id → process`).
* `meta`: lagrar starttid och storlek per flow.
* `seq`: räknare för att ge varje flow ett unikt ID.
* `fcts`: lista där alla **Flow Completion Times** sparas.
* `t0`: starttid för hela experimentet.
* `next_tick`: tidpunkt då nästa “batch” av flöden ska startas (1 sekund mellan varje).

---

# 🔹 5️⃣ Huvudloopen – skapa och mäta trafik

```python
while (time.time() - t0) < duration or in_flight:
```

Den här loopen körs så länge experimentet pågår (och tills alla flöden är klara).
Två saker händer inuti:

---

## 🧩 a) Starta nya flöden varje sekund

```python
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
```

### 🔍 Vad som händer:

* Varje sekund (`now >= next_tick`) startas `intensity` antal nya flöden.
* Varje flöde:

  1. Får ett unikt ID (`seq`).
  2. Slumpas fram en storlek (`size_b`) via eCDF.
  3. Startar en iperf-klient på `src` som skickar data till `dst`.
  4. Lagrar starttid och storlek i `meta`.

🧠 Exempel:
Om `intensity=4` och `duration=10`, startas 4 nya flöden varje sekund under 10 sekunder → totalt 40 flöden.

---

## 🧩 b) Kolla om flöden är färdiga

```python
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
```

### 🔍 Vad som händer:

* `proc.poll()` returnerar `None` om processen fortfarande körs, annars betyder det att flödet är klart.
* Beräkna **Flow Completion Time (FCT)**:

  ```python
  fct = end - start
  ```
* Spara resultatet i `fcts`.
* Om `on_done` (callback) är satt → skicka en loggrad med alla metadata (kallas i `ExperimentHandler`).
* Ta bort flödet från `in_flight` (det är nu avslutat).

💡 FCT är den centrala mätningen i experimentet — den visar **hur snabbt flöden avslutas** under olika belastningsnivåer.

---

# 🔹 6️⃣ Vänta en liten stund mellan iterationerna

```python
time.sleep(0.01)
```

Förhindrar att loopen körs för snabbt (CPU-snålt).

---

# 🔹 7️⃣ Stäng iperf-servern

```python
finally:
    recv.terminate()
```

När alla flöden är färdiga avslutas iperf-servern på mottagarsidan.

---

# 🔹 8️⃣ Returnera alla FCT-värden

```python
return fcts
```

Funktionen returnerar en lista med alla flow completion times i sekunder.
Dessa används sedan för statistik och plottning.

---

# 🔹 9️⃣ Sammanfattning i punktform

| Del             | Vad den gör                                   |
| --------------- | --------------------------------------------- |
| `get_sampler()` | Hämtar trafiksamplare (WebSearch/DataMining)  |
| `iperf -s`      | Startar server på mottagaren                  |
| `iperf -c`      | Startar klientflöden från sändaren            |
| `intensity`     | Antal nya flöden per sekund                   |
| `duration`      | Hur länge nya flöden startas                  |
| `FCT`           | Flow Completion Time, mäts för varje flöde    |
| `on_done`       | Callback som loggar varje flöde i JSON-format |
| `return fcts`   | Returnerar lista av alla FCT:er för analys    |

---

# 💡 Kortfattat

> `genDCTraffic()` simulerar realistisk datacentertrafik mellan två värdar med olika intensitet och flödesstorlek.
> Den startar flera iperf-flöden, mäter deras avslutningstider (FCT), och loggar resultaten.
>
> WebSearch-trafik består mest av små, snabba flöden — DataMining består av större, långsammare flöden.
>
> Resultaten används för att analysera hur nätverkets prestanda påverkas av belastning och trafiktyp.



# 🧩 Experiment

```python
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
```

---

# 🧠 Vad klassen gör

Klassen `Experiment` är **en teststyrning (experiment runner)** som automatiserar trafikexperimentet i ditt datacenter-nätverk.

Den:

1. Hämtar alla Mininet-hosts (`h1–h4`),
2. Slumpar vilka två som kommunicerar (källa och destination),
3. Kör trafik för båda trafiktyperna (WebSearch och DataMining),
4. Ökar trafikintensiteten stegvis (1 → 10 flöden/s),
5. Loggar alla Flow Completion Times (FCT) med hjälp av `FlowLogger`.

---

# 🔹 1️⃣ Konstruktor (`__init__`)

```python
def __init__(self, net):
    self.net = net
    self.logger = FlowLogger()
```

### 🔍 Förklaring

* `net`: är en Mininet-instans som redan skapats (med topologin `OnePodFatTree`).
* `self.net`: sparar referensen så att experimentet kan hämta hosts.
* `self.logger = FlowLogger()` skapar en logger som skriver varje avslutat flöde till en fil, vanligtvis `flows.jsonl`.

💡 **Tänk på detta som:**

> “Experimentet behöver veta vilka hosts som finns i nätet och ha någon som skriver ner resultaten.”

---

# 🔹 2️⃣ Callback-funktion för färdiga flöden (`_on_done`)

```python
def _on_done(self, rec):
    print(f"[Flow] {rec}")
    self.logger.write(rec)
```

### 🔍 Vad den gör:

* Denna funktion kallas automatiskt varje gång ett flöde avslutas (från `genDCTraffic()` via `on_done`).
* `rec` är en dictionary med information om flödet:

  ```python
  {"src": "h1", "dst": "h4", "traffic_type": 1,
   "intensity": 3, "size_bytes": 50000, "fct_s": 0.12}
  ```
* Skriver ut en loggrad i terminalen.
* Skickar posten vidare till `FlowLogger` för att sparas i fil.

🧠 Det betyder:

> Varje gång ett flöde slutar, visas det direkt på skärmen och loggas i en datafil.

---

# 🔹 3️⃣ Kör experimentet (`run()`)

```python
def run(self, times=10, intensity=10, duration=10):
```

### 🔍 Parametrar:

| Parameter   | Betydelse                                                |
| ----------- | -------------------------------------------------------- |
| `times`     | Hur många experimentomgångar (repetitioner) ska köras    |
| `intensity` | Max antal flöden per sekund (ökar stegvis från 1 till N) |
| `duration`  | Hur länge varje intensitet körs (sekunder)               |

💡 Exempel:
`run(times=10, intensity=10, duration=10)` betyder att du:

* Kör 10 omgångar,
* Varje gång ökar flödesintensiteten från 1 till 10 flows/s,
* Varje nivå pågår i 10 sekunder.

---

# 🔹 4️⃣ Hämta hosts från Mininet

```python
hosts = [self.net.get(f"h{i}") for i in range(1, 5)]
```

* Hämtar alla hosts (`h1`, `h2`, `h3`, `h4`) från nätverket.
* `self.net.get()` är en Mininet-funktion för att hämta noder baserat på namn.

---

# 🔹 5️⃣ Upprepa experimentet flera gånger

```python
for rep in range(times):
    src, dst = random.sample(hosts, 2)
    print(f"\n[Run {rep+1}/{times}] {src.name} → {dst.name}")
```

* Kör `times` upprepningar.
* Väljer slumpmässigt **två olika hosts** för varje körning — en som sändare (`src`), en som mottagare (`dst`).
* Skrivs ut i terminalen, t.ex.:

  ```
  [Run 3/10] h2 → h4
  ```

💡 Det här simulerar trafik mellan olika servrar i datacentret.

---

# 🔹 6️⃣ Kör båda trafiktyperna

```python
for t in (1, 2):
    label = "WebSearch" if t==1 else "DataMining"
    print(f"  Type={label}")
```

* Loopar över två trafiktyper:

  * `1` = WebSearch
  * `2` = DataMining
* Skrivs ut i terminalen:

  ```
  Type=WebSearch
  Type=DataMining
  ```

🧠 På så sätt kör du **två olika trafikprofiler** under samma experiment.

---

# 🔹 7️⃣ Öka trafikintensiteten steg för steg

```python
for bulk in range(1, intensity+1):
    print(f"    Intensity {bulk}/{intensity}")
    genDCTraffic(src, dst, t, bulk, duration, on_done=self._on_done)
```

### 🔍 Vad som händer:

* Kör experimentet med ökande intensitet: 1, 2, 3, ... upp till `intensity`.
* Varje gång:

  * `bulk` anger hur många flöden per sekund som startas.
  * `duration` hur länge det pågår (sekunder).
  * `genDCTraffic()` startar trafiken och loggar resultaten.
* Callback `on_done=self._on_done` gör att varje färdigt flöde skrivs till loggfilen.

Exempel i terminalen:

```
[Run 1/10] h2 → h4
  Type=WebSearch
    Intensity 1/10
    Intensity 2/10
  Type=DataMining
    Intensity 1/10
    Intensity 2/10
```

---

# 🔹 8️⃣ Hur experimentet går till (översikt)

För varje iteration (`Run`):

1. Välj slumpmässigt vilka hosts som kommunicerar.
2. Kör först WebSearch, sedan DataMining.
3. Öka intensiteten stegvis.
4. För varje flöde: mät och logga FCT.
5. När alla flöden är klara → gå vidare till nästa repetition.

---

# 🔹 9️⃣ Sammanfattning i punktform

| Steg | Vad som händer                              |
| ---- | ------------------------------------------- |
| 1    | Hämta hosts från Mininet                    |
| 2    | Slumpa sändare/mottagare                    |
| 3    | Kör båda trafiktyper (WebSearch/DataMining) |
| 4    | Öka intensiteten (1 → N flows/s)            |
| 5    | Starta iperf-flöden med `genDCTraffic()`    |
| 6    | Logga varje flöde via `_on_done()`          |
| 7    | Repetera experimentet flera gånger          |

---

# 💡 Kortfattat

> Klassen `Experiment` styr hela experimentkörningen.
> Den väljer slumpmässigt två hosts, kör både WebSearch- och DataMining-trafik,
> ökar belastningen stegvis, och loggar resultat (Flow Completion Time, FCT)
> för varje flöde via `FlowLogger`.

På så sätt kan du:

* jämföra prestanda mellan trafiktyper,
* se hur FCT förändras med ökad intensitet,
* analysera effekten av Round Robin Load Balancing i din Ryu-controller.

---
