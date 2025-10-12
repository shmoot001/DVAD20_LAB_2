#!/usr/bin/env python3
"""
Round Robin Load Balancer (Lab 2)
---------------------------------
Implements L3-style switching using Ryu and OpenFlow 1.3.
Performs MAC learning and Round Robin load balancing
for aggregation switches (s2, s4). Includes logging
and flow timeouts for dynamic updates.
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types, ipv4


class RoundRobinLB(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(RoundRobinLB, self).__init__(*args, **kwargs)
        self.mac_to_port = {}          # MAC learning per switch
        self.rr_counter = {}           # Round Robin counter per switch
        self.logger.info("[Init] RoundRobinLB started.")

    # ---------------------------
    # Helper: install flow rule
    # ---------------------------
    def add_flow(self, datapath, priority, match, actions, buffer_id=None,
                 idle=10, hard=30):
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, idle_timeout=idle,
                                    hard_timeout=hard, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    idle_timeout=idle, hard_timeout=hard,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)
        self.logger.debug(f"[Flow Added] DPID={datapath.id}, Match={match}, Actions={actions}")

    # ---------------------------
    # Switch connection
    # ---------------------------
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        # Table-miss: send to controller
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
        self.rr_counter[datapath.id] = 0
        self.logger.info(f"[Switch Connected] Switch {datapath.id}")

    # ---------------------------
    # Main packet handling
    # ---------------------------
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        # Skip LLDP
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dst, src = eth.dst, eth.src
        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        # Learn MAC address
        self.mac_to_port[dpid][src] = in_port
        self.logger.debug(f"[Learn] DPID={dpid} {src}->{in_port}")

        # Determine output port
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

        actions = [parser.OFPActionOutput(out_port)]

        # Add flow only for IPv4 packets (ARP handled statically)
        if eth.ethertype == ether_types.ETH_TYPE_IP:
            ip_pkt = pkt.get_protocol(ipv4.ipv4)
            match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP,
                                    ipv4_src=ip_pkt.src, ipv4_dst=ip_pkt.dst)
            self.add_flow(datapath, 1, match, actions)
            self.logger.debug(f"[IPv4 Flow] {ip_pkt.src}->{ip_pkt.dst} via port {out_port}")

        # Send the packet out immediately
        data = None if msg.buffer_id != ofproto.OFP_NO_BUFFER else msg.data
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)
