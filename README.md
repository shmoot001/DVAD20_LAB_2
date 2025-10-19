# 1. Klassdefinition och initiering

    class RoundRobinLB(app_manager.RyuApp):
        OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

        def __init__(self, *args, **kwargs):
            super(RoundRobinLB, self).__init__(*args, **kwargs)
            self.mac_to_port = {}          # Maps each MAC address to its port
            self.rr_counter = {}           # Keeps track of which uplink port to use next
            self.logger.info("[Init] RoundRobinLB started.")


    Klassen ärver från RyuApp → gör den körbar som controller-applikation.

    mac_to_port är en tabell som för varje switch (DPID) lagrar vilka MAC-adresser den lärt sig på vilka portar.
    → t.ex. {1: {'00:00:00:00:00:01': 1, '00:00:00:00:00:02': 2}}

    rr_counter håller koll på vilket uplink-nummer som ska användas nästa gång.

    logger.info skriver ut loggar så du kan följa händelser i terminalen.


## 2. 🧩 add_flow

```python
def add_flow(self, datapath, priority, match, actions, buffer_id=None,
             idle=10, hard=30):
```

Den här funktionen används för att **lägga till (installera) en flow-regel i en OpenFlow-switch**.

En **flow-regel** är som en *instruktion* som säger:

> “När ett paket matchar vissa villkor (t.ex. IP-adress eller MAC), gör de här åtgärderna (t.ex. skicka till port 2).”

Det är grunden i hur en SDN-controller styr trafiken i nätet — istället för att varje paket måste skickas till controllern, **installeras regler** i switchen så att framtida paket går direkt i dataplanet.

---

# 🔹 Förklaring av parametrarna

| Parameter   | Typ                 | Förklaring                                                                                                         |
| ----------- | ------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `datapath`  | objekt              | Representerar den OpenFlow-switch som regeln ska installeras på.                                                   |
| `priority`  | int                 | Bestämmer vilken regel som gäller om flera matchar samma paket (högre = viktigare).                                |
| `match`     | objekt (`OFPMatch`) | Specificerar vilka paket som ska matchas (t.ex. baserat på IP, MAC, port, etc.).                                   |
| `actions`   | lista               | Lista av `OFPAction`-objekt som anger vad switchen ska göra med matchande paket (t.ex. `OFPActionOutput(port=2)`). |
| `buffer_id` | int, optional       | Identifierar ett buffrat paket i switchen som regeln ska tillämpas på direkt.                                      |
| `idle`      | int                 | Hur länge (i sekunder) regeln får ligga kvar utan att användas innan den tas bort (idle timeout).                  |
| `hard`      | int                 | Hur länge (i sekunder) regeln får ligga kvar totalt innan den tas bort (hard timeout).                             |

---

# 🔹 Steg-för-steg genomgång av koden

### 1️⃣ Hämta hjälpklasser från datapath

```python
parser = datapath.ofproto_parser
ofproto = datapath.ofproto
```

* `datapath` är själva “kanalen” mellan controllern och switchen.
* `datapath.ofproto_parser` används för att **skapa OpenFlow-meddelanden**.
* `datapath.ofproto` innehåller konstanter och typer (t.ex. `OFPIT_APPLY_ACTIONS`).

🧠 Tänk på `parser` som "verktygslådan" du använder för att bygga OpenFlow-kommandon.

---

### 2️⃣ Skapa instruktionen som ska tillämpas

```python
inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
```

* `OFPInstructionActions` säger till switchen *vilken lista av actions* den ska utföra när ett paket matchar regeln.
* Här använder du `APPLY_ACTIONS`, vilket betyder:
  **”Utför dessa actions direkt på paketet.”**

💡 Det här är ofta `output(port)` för att skicka paketet vidare till rätt gränssnitt.

---

### 3️⃣ Skapa själva FlowMod-meddelandet

#### Om vi har ett `buffer_id`:

```python
if buffer_id:
    mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                            priority=priority, idle_timeout=idle,
                            hard_timeout=hard, match=match,
                            instructions=inst)
```

* Detta betyder att switchen redan har **buffrat** ett paket som väntar på ett beslut.
* Vi installerar regeln och **tillämpas direkt på det buffrade paketet**.
  → Inget extra “packet out”-meddelande behövs.

#### Om vi inte har något `buffer_id`:

```python
else:
    mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                            idle_timeout=idle, hard_timeout=hard,
                            match=match, instructions=inst)
```

* Då skapas en vanlig FlowMod (utan att appliceras på något specifikt buffrat paket).
* Switch installerar regeln i sin flow table och använder den för framtida trafik.

---

### 4️⃣ Skicka FlowMod till switchen

```python
datapath.send_msg(mod)
```

Detta skickar själva kommandot till switchen över den etablerade TCP-kanalen mellan Ryu och OVS (Open vSwitch).

➡️ När switchen får det, lägger den in regeln i sin **flow table**.

---

### 5️⃣ Logga vad som installerats

```python
self.logger.debug(f"[Flow Added] DPID={datapath.id}, Match={match}, Actions={actions}")
```

Skriver ut i terminalen vilken switch (`DPID` = Datapath ID) regeln lades till på, vilka matchningskriterier som användes, och vilka actions som ska utföras.

---

# 🔹 Vad händer praktiskt efter detta?

1. **Första paketet** i ett nytt flöde (t.ex. TCP-session mellan h1 och h4) matchar ingen regel → table-miss → skickas till controllern.
2. Controllern kallar `add_flow()` för att lägga till en regel i switchen:

   * match: `ipv4_src=10.0.0.1`, `ipv4_dst=10.0.0.4`
   * action: `output:2`
3. **Framtida paket** från samma källa/destination matchar regeln direkt i switchen → går snabbare (ingen controller-inblandning).
4. Om ingen trafik sker på 10 sekunder → regeln tas bort (idle timeout).
   Om den legat i 30 sekunder totalt → tas bort ändå (hard timeout).

---

# 🔹 Grafiskt exempel (förenklat)

```
[ Controller (Ryu) ]
       |
       |  (FlowMod)
       v
[ Switch Flow Table ]
+----------------------------+
| Priority | Match | Action  |
|-----------|--------|--------|
| 1         | IP 1→4 | out:2  |
| 0         | *      | CONTROLLER |
+----------------------------+
```

Första raden installerades via `add_flow()`, andra är din table-miss-rule.

---

# 🔹 Sammanfattning i punktform

| Funktion                                 | Beskrivning                                                                            |
| ---------------------------------------- | -------------------------------------------------------------------------------------- |
| **Vad gör den?**                         | Lägger till en ny flow-regel i switchens flow table.                                   |
| **När används den?**                     | När controllern vill instruera switchen att hantera framtida trafik direkt.            |
| **Varför behövs den?**                   | För att minska belastningen på controllern och möjliggöra snabbare dataplan-hantering. |
| **Vad händer om man inte använder den?** | Alla paket skulle gå via controllern → långsamt och ineffektivt.                       |
| **Vilka timeouts finns?**                | `idle_timeout` (ingen trafik → ta bort), `hard_timeout` (oavsett aktivitet → ta bort). |

---

💡 **Kortfattat:**

> `add_flow()` är den funktion som faktiskt “programmerar” switchen.
> Den säger: *"När du ser paket som matchar dessa fält, gör dessa åtgärder — och ta bort regeln efter en viss tid."*
>
> Det är den viktigaste byggstenen i hur din Ryu-controller styr nätet.




## 3. 🧩 switch_features_handler

```python
@set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
def switch_features_handler(self, ev):
    datapath = ev.msg.datapath
    parser = datapath.ofproto_parser
    ofproto = datapath.ofproto

    # Install table-miss flow entry
    match = parser.OFPMatch()
    actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                      ofproto.OFPCML_NO_BUFFER)]
    self.add_flow(datapath, 0, match, actions)
    self.rr_counter[datapath.id] = 0
    self.logger.info(f"[Switch Connected] Switch {datapath.id}")
```

---

# 🧠 Översikt: vad funktionen gör

`switch_features_handler()` körs **en gång per switch**, direkt när den har anslutit till controllern via OpenFlow.
Den:

1. Identifierar den anslutna switchen.
2. Installerar en **table-miss rule** (defaultregel).
3. Initierar Round Robin-räknaren för just den switchen.
4. Loggar anslutningen i terminalen.

Kort sagt:

> “När en ny switch kopplar upp sig, sätt upp grundregler så att controllern får alla okända paket.”

---

# 🔹 1️⃣ Händelsehanteraren (EventOFPSwitchFeatures)

```python
@set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
```

### 🔍 Vad betyder detta?

* `@set_ev_cls` är en **dekorator** som berättar för Ryu att den här funktionen ska anropas när en viss typ av event inträffar.
* `ofp_event.EventOFPSwitchFeatures` är händelsen som inträffar **när en switch skickar sina "features" till controllern** under anslutningen.
* `CONFIG_DISPATCHER` betyder att vi hanterar händelsen i stadiet där switchen är **redo att ta emot konfigurationskommandon** (men inte ännu hanterar datapaket).

🧠 Du kan tänka det som att controllern säger:

> “Hej, du är nu ansluten. Låt mig konfigurera din tabell innan du börjar skicka trafik.”

---

# 🔹 2️⃣ Hämta datapath och protokoll

```python
datapath = ev.msg.datapath
parser = datapath.ofproto_parser
ofproto = datapath.ofproto
```

| Variabel   | Förklaring                                                                          |
| ---------- | ----------------------------------------------------------------------------------- |
| `datapath` | Representerar själva switchen (kommunikationskanalen mellan controller och switch). |
| `parser`   | Används för att skapa OpenFlow-meddelanden som `OFPMatch`, `OFPFlowMod`, etc.       |
| `ofproto`  | Innehåller konstanter som `OFPP_CONTROLLER`, `OFPCML_NO_BUFFER`, osv.               |

💡 **Datapath = switchen.**
Controllern använder `datapath` för att skicka instruktioner (t.ex. installera flow-regler) till switchen.

---

# 🔹 3️⃣ Skapa och installera “table-miss rule”

```python
match = parser.OFPMatch()
actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                  ofproto.OFPCML_NO_BUFFER)]
self.add_flow(datapath, 0, match, actions)
```

### 🔍 Vad betyder det här?

1. `parser.OFPMatch()`
   → Skapar ett tomt match-objekt = *matcha alla paket*.

2. `actions = [parser.OFPActionOutput(...)]`
   → Säger till switchen vad den ska göra med paket som inte matchar någon regel.
   I det här fallet: **skicka paketet till controllern.**

3. `self.add_flow(...)`
   → Installerar själva regeln i switchens flow table.
   Prioritet (`priority=0`) gör att detta blir den **lägsta** regeln, alltså den som bara aktiveras om inget annat matchar.

### 🧩 Resultat:

Switchens flow table innehåller nu följande regel:

| Priority | Match       | Action             |
| -------- | ----------- | ------------------ |
| 0        | (match all) | output: CONTROLLER |

---

# 🔹 Varför behövs detta?

Utan den här regeln skulle switchen **slänga alla paket som inte matchar en regel** — alltså all ny trafik som controllern ännu inte känner till.

Med denna table-miss rule:

* Nya flöden skickas till controllern.
* Controllern kan analysera paketen (t.ex. via `_packet_in_handler`).
* Den bestämmer var paketet ska skickas.
* Och den installerar en ny flow-regel för framtida paket.

🧠 Det här är alltså grunden för dynamisk styrning i SDN:

> “Alla okända paket går till controllern, som sedan lär sig och programmerar switchen.”

---

# 🔹 4️⃣ Initiera Round Robin-räknaren

```python
self.rr_counter[datapath.id] = 0
```

* Varje switch får ett unikt **Datapath ID (DPID)**, t.ex. s1 = 1, s2 = 2, osv.
* Här initieras en **Round Robin-counter** till 0 för just denna switch.
* Aggregationsswitcharna (s2, s4) använder detta för att växla mellan uplink-portar senare.

Exempel:

```
self.rr_counter = {
   1: 0,
   2: 0,
   3: 0,
   4: 0
}
```

Det betyder att när s2 får sitt första paket, kommer den börja med uplink port 1 (`0 % 2 = 0`), nästa gång port 2 (`1 % 2 = 1`), osv.

---

# 🔹 5️⃣ Loggning

```python
self.logger.info(f"[Switch Connected] Switch {datapath.id}")
```

Skriver till terminalen att en switch har anslutit och fått sin grundkonfiguration.
Exempelutskrift:

```
[Switch Connected] Switch 2
```

Det hjälper dig som användare att bekräfta att anslutningen och table-miss-regeln installerats korrekt.

---

# 🔹 🧠 Sammanfattning av hela funktionen

| Steg | Händelse                                         | Vad som sker                                                |
| ---- | ------------------------------------------------ | ----------------------------------------------------------- |
| 1    | Switch ansluter till controllern                 | Event `EventOFPSwitchFeatures` triggas                      |
| 2    | Controller hämtar datapath (kommunikationskanal) | Gör sig redo att konfigurera switchen                       |
| 3    | Table-miss rule installeras                      | Paket som inte matchar någon regel skickas till controllern |
| 4    | Round Robin-räknare initieras                    | Gör att RR-logiken fungerar senare i `_packet_in_handler`   |
| 5    | Loggning sker                                    | Du ser i terminalen att switchen är online                  |

---

# 🔹 Pedagogisk analogi 🎓

Tänk dig att switchen är en **ny anställd på ett företag** och controllern är **chefen**.

1. Den nya anställda (switch) börjar sitt jobb (ansluter).
2. Chefen (controller) säger:

   > “Om du inte vet vad du ska göra med ett dokument (ett paket), skicka det till mig.”
3. Chefen noterar också vem det är (datapath.id = switch-ID).
4. Chefen loggar i sin journal: “Ny anställd klar för uppgifter.”

Efter detta kan den anställda börja ta emot riktiga arbetsuppgifter (paket), och allt som är oklart går till chefen för beslut.

---

# 🔹 Sammanfattning i punktform

| Del                      | Beskrivning                                                                 |
| ------------------------ | --------------------------------------------------------------------------- |
| **Vad gör funktionen?**  | Hanterar när en switch ansluter till controllern.                           |
| **När körs den?**        | Direkt efter att en switch skickar sina OpenFlow-features till controllern. |
| **Vad installerar den?** | En “table-miss rule” som fångar alla okända paket.                          |
| **Varför behövs den?**   | För att controllern ska kunna ta emot nya flöden och fatta routingbeslut.   |
| **Vad mer gör den?**     | Initierar en Round Robin-räknare för lastbalansering.                       |
| **Resultat**             | Switchar är nu redo att börja forwarda trafik med hjälp av controllern.     |

---

💡 **Kort sagt:**

> `switch_features_handler()` är startpunkten för varje switch i nätverket.
> Den installerar den viktiga “table-miss rule” som gör att nya paket skickas till controllern,
> och förbereder grunden för Round Robin-logiken.





# 4. 🧩 _packet_in_handler

```python
@set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
def _packet_in_handler(self, ev):
```

Den här funktionen kallas automatiskt varje gång ett **PacketIn-event** inträffar — alltså när en switch inte hittar någon matchande flow-regel för ett paket och skickar det till controllern.

**Tänk på det som:**

> "Hej controller, jag vet inte vart jag ska skicka det här paketet — hjälp mig att bestämma!"

---

# 🔹 Steg 1: Hämta nödvändig information

```python
msg = ev.msg
datapath = msg.datapath
parser = datapath.ofproto_parser
ofproto = datapath.ofproto
in_port = msg.match['in_port']
```

| Kod        | Förklaring                                                             |
| ---------- | ---------------------------------------------------------------------- |
| `msg`      | Innehåller hela meddelandet från switchen.                             |
| `datapath` | Representerar switchen som skickade paketet (har unikt ID = DPID).     |
| `parser`   | Verktyg för att skapa OpenFlow-meddelanden (t.ex. FlowMod, PacketOut). |
| `ofproto`  | Innehåller konstanter (som `OFPP_CONTROLLER`, `OFPP_FLOOD`, osv.).     |
| `in_port`  | Den port på switchen där paketet kom in.                               |

🧠 Controllern behöver detta för att veta *vilken switch och port* paketet kom ifrån — annars vet den inte hur topologin ser ut.

---

# 🔹 Steg 2: Tolka paketet (packet parsing)

```python
pkt = packet.Packet(msg.data)
eth = pkt.get_protocols(ethernet.ethernet)[0]
```

* `packet.Packet()` skapar ett Ryu-objekt som låter oss analysera paketets innehåll.
* `eth` är Ethernet-delen av paketet → innehåller:

  * **käll-MAC** (`eth.src`)
  * **destinations-MAC** (`eth.dst`)
  * **ethertype** (vilken typ av protokoll som följer, t.ex. IPv4 eller LLDP)

---

# 🔹 Steg 3: Ignorera LLDP-paket

```python
if eth.ethertype == ether_types.ETH_TYPE_LLDP:
    return
```

* **LLDP (Link Layer Discovery Protocol)** används av Ryu för topologidiscovery (switchar berättar för varandra att de finns).
* Vi **vill inte routa eller balancera** LLDP-paket, så vi hoppar över dem.

🧠 Om vi inte gjorde det här skulle controllern försöka behandla interna nätverksmeddelanden som vanlig trafik — vilket kan orsaka loopar.

---

# 🔹 Steg 4: MAC-inlärning (Layer-2 learning)

```python
dst, src = eth.dst, eth.src
dpid = datapath.id
self.mac_to_port.setdefault(dpid, {})
self.mac_to_port[dpid][src] = in_port
self.logger.debug(f"[Learn] DPID={dpid} {src}->{in_port}")
```

Här lär sig controllern **vilken port en viss MAC-adress finns på**.
Detta kallas **MAC learning**, samma princip som vanliga Ethernet-switchar använder.

🧠 Exempel:

* Om paketet kommer från host `h1` med MAC `00:00:00:00:00:01` på port 1
  → controllern sparar `{'00:00:00:00:00:01': 1}` för just den switchen (DPID).

Nästa gång ett paket ska till samma MAC, behöver vi **inte flooda** – vi vet redan vart det ska.

---

# 🔹 Steg 5: Välj utport (Round Robin eller Flood)

```python
if dst in self.mac_to_port[dpid]:
    out_port = self.mac_to_port[dpid][dst]
else:
    if dpid in [2, 4]:  # aggregation switches
        uplink_ports = [1, 2]
        counter = self.rr_counter[dpid]
        out_port = uplink_ports[counter % len(uplink_ports)]
        self.rr_counter[dpid] += 1
        self.logger.info(f"[RR] Switch={dpid} selected uplink={out_port}")
    else:
        out_port = ofproto.OFPP_FLOOD
```

Det här är **beslutsdelen** i din controller.

### 🧠 Vad som händer:

1. Om destinationen är känd (`dst` finns i mac_to_port) →
   → Skicka direkt till rätt port (`out_port = mac_to_port[dpid][dst]`).
2. Om den är **okänd**:

   * Om det är en **aggregationsswitch (s2 eller s4)** → använd **Round Robin** mellan port 1 och 2.
   * Annars → flooda paketet ut på alla portar (`OFPP_FLOOD`).

### ⚙️ Så fungerar Round Robin:

```python
counter = self.rr_counter[dpid]
out_port = uplink_ports[counter % len(uplink_ports)]
self.rr_counter[dpid] += 1
```

* Om `counter = 0` → port 1
* Om `counter = 1` → port 2
* Sedan tillbaka till port 1 igen (0,1,0,1,...)

Detta fördelar nya flöden **jämnt mellan uplinks**, vilket skapar lastbalansering.

---

# 🔹 Steg 6: Definiera vad som ska göras (actions)

```python
actions = [parser.OFPActionOutput(out_port)]
```

* Här berättar vi för switchen att den ska **skicka paketet vidare** till `out_port`.
* Detta är själva "action" som sen används i både:

  * `add_flow()` (för framtida paket)
  * `PacketOut` (för det aktuella paketet)

---

# 🔹 Steg 7: Installera en flow-regel (för IPv4-trafik)

```python
if eth.ethertype == ether_types.ETH_TYPE_IP:
    ip_pkt = pkt.get_protocol(ipv4.ipv4)
    match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP,
                            ipv4_src=ip_pkt.src, ipv4_dst=ip_pkt.dst)
    self.add_flow(datapath, 1, match, actions)
    self.logger.debug(f"[IPv4 Flow] {ip_pkt.src}->{ip_pkt.dst} via port {out_port}")
```

**Varför gör vi detta?**

* För att nästa gång samma IP-par kommunicerar, ska switchen kunna hantera paketet direkt – utan att fråga controllern igen.
* Vi matchar endast på IPv4 (inte ARP eller LLDP).
* `priority=1` → högre än table-miss-regeln (som har 0).

**Effekt:** framtida paket med samma käll- och destinations-IP matchar denna regel och går direkt till rätt port → snabbare nätverk.

---

# 🔹 Steg 8: Skicka ut paketet (PacketOut)

```python
data = None if msg.buffer_id != ofproto.OFP_NO_BUFFER else msg.data
out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                          in_port=in_port, actions=actions, data=data)
datapath.send_msg(out)
```

Det här ser till att **det aktuella paketet** faktiskt skickas ut i nätet direkt, medan flow-regeln installeras i bakgrunden.

* `PacketOut` → OpenFlow-meddelande som säger:
  “Skicka ut detta paket på port X”.
* `buffer_id` → om switchen redan buffrade paketet används det; annars skickas `msg.data` (hela paketet).

---

# 🔹 Steg 9: Summering av logiken

| Steg | Händelse                    | Vad som sker                                                         |
| ---- | --------------------------- | -------------------------------------------------------------------- |
| 1    | Paket kommer till switchen  | Ingen matchande regel → skickas till controllern                     |
| 2    | Controller läser paketet    | Identifierar käll- och destinations-MAC                              |
| 3    | Controller lär sig käll-MAC | Sparar vilken port den kom ifrån                                     |
| 4    | Destination känd?           | Ja → skicka direkt, Nej → Round Robin (på s2/s4) eller Flood         |
| 5    | IPv4-trafik?                | Ja → installera flow-regel med `add_flow()`                          |
| 6    | Skicka ut paketet           | Controller beordrar switchen att forwarda paketet direkt             |
| 7    | Nästa paket                 | Går direkt via flow-regeln i switchen (ingen controller-inblandning) |

---

# 🔹 Pedagogisk analogi 🎓

Tänk dig att switchen är en **receptionist** på ett kontor:

1. En ny besökare (paket) kommer in.
2. Receptionisten kollar om den personen finns i listan (MAC-tabell).
3. Om personen inte finns:

   * Receptionisten skickar upp personen till en **koordinator (controller)** som bestämmer vart den ska.
   * Koordinatorn säger “nästa gång någon tillhörande den här gruppen kommer – gå direkt till rum A”.
4. Receptionisten antecknar detta (flow-regel) så nästa besök går snabbare.

---

# 🔹 Sammanfattning

| Del                   | Funktion                                           | Syfte                                  |
| --------------------- | -------------------------------------------------- | -------------------------------------- |
| **PacketIn-event**    | Aktiveras när switchen inte vet vart ett paket ska | Gör att controllern kan ta beslut      |
| **MAC-inlärning**     | Sparar käll-MAC → port                             | Undviker flood vid nästa gång          |
| **Round Robin**       | Växlar mellan två uplinks (port 1, 2)              | Fördelar belastningen jämnt            |
| **Flow-installation** | Lägger till en regel i switchen                    | Framtida paket går direkt via switchen |
| **PacketOut**         | Skickar nuvarande paket ut i nätet                 | Paketet levereras omedelbart           |

---

💡 **Kort sagt:**

> `_packet_in_handler()` är controllerns “hjärna” — den lär sig topologin, väljer rätt port med Round Robin-balansering, installerar flow-regler för snabbare framtida trafik, och ser till att första paketet faktiskt skickas iväg.



# How to run the code : 
# sudo killall ovs-testcontroller
# sudo pkill -f ryu-manager
# conda activate ryu
# ryu-manager rr_lb.py --verbose
# sudo python3 experiment.py
