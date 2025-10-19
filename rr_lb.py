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
        self.mac_to_port = {}          # Maps each MAC address to its port
        self.rr_counter = {}           # Keeps track of which uplink port to use next
        self.logger.info("[Init] RoundRobinLB started.")

    # ---------------------------
    # install flow rule 
    # Description: Installs a flow rule on the switch
    # Parameters:
    # - datapath: the switch to install the flow on
    # - priority: the priority level of the flow
    # - match: the match criteria for the flow (IP-address)
    # - actions: the actions to take when the flow matches (e.g., Send to port 2)
    # - buffer_id: the buffer ID for the flow (optional)
    # - idle: idle timeout for the flow (default: 10 seconds)
    # - hard: hard timeout for the flow (default: 30 seconds)
    # ---------------------------
    def add_flow(self, datapath, priority, match, actions, buffer_id=None,
                 idle=10, hard=30):
        # Get parser for the datapath
        parser = datapath.ofproto_parser
        # Construct flow mod message and send it to datapath
        ofproto = datapath.ofproto
        # Create instruction to apply actions
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        # Create flow mod message
        if buffer_id:
            # Use buffer_id if provided
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, idle_timeout=idle,
                                    hard_timeout=hard, match=match,
                                    instructions=inst)
        else:
            # Otherwise, create flow mod without buffer_id
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    idle_timeout=idle, hard_timeout=hard,
                                    match=match, instructions=inst)
        # Send flow mod message to datapath
        datapath.send_msg(mod)
        self.logger.debug(f"[Flow Added] DPID={datapath.id}, Match={match}, Actions={actions}")

    # ---------------------------
    # Switch connection
    # Description: Handles switch connection events
    # EventOFPSwitchFeatures : This event is triggered when a switch connects to the controller and provides its features.
    # Parameters:
    # - ev: the event message containing switch features
    # ---------------------------
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        # Install table-miss flow entry
        match = parser.OFPMatch()
        # Table-miss: send to controller
        # Why is priority 0? Table-miss flow entries must have the lowest priority to ensure they match packets that do not match any other flow entries.
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
        self.rr_counter[datapath.id] = 0
        self.logger.info(f"[Switch Connected] Switch {datapath.id}")

    # ---------------------------
    # Main packet handling
    # Description: Handles incoming packets and performs MAC learning and Round Robin load balancing
    # EventOFPPacketIn : This event is triggered when a packet arrives at the switch
    # Parameters:
    # - ev: the event message containing the packet data
    # ---------------------------
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        # Get the input port from the message
        in_port = msg.match['in_port']
        # Parse the packet
        pkt = packet.Packet(msg.data)
        # Get the Ethernet protocol part of the packet (e.g., src/dst MAC)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        # Skip LLDP
        # Why skip LLDP? LLDP packets are used for network topology discovery and should not be processed for forwarding decisions.
        # What is LLDP? Link Layer Discovery Protocol (LLDP) is a protocol used by network devices to advertise their identity and capabilities to neighboring devices.
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        # Get source and destination MAC addresses
        dst, src = eth.dst, eth.src
        # Get datapath ID to identify the switch
        dpid = datapath.id
        # Initialize mac_to_port for this switch if not already done
        self.mac_to_port.setdefault(dpid, {})

        # Learn the source MAC to avoid FLOOD next time
        self.mac_to_port[dpid][src] = in_port
        self.logger.debug(f"[Learn] DPID={dpid} {src}->{in_port}")
        # Determine the output port
        # If the destination MAC is known, use the learned port
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            # If destination MAC is unknown, apply Round Robin for aggregation switches
            # How does Round Robin work here? It cycles through the available uplink ports for each new flow to balance the load.
            # Which switches use Round Robin? Only aggregation switches (s2, s4) use Round Robin; others flood unknown destinations.
            # Identify aggregation switches by their DPID
            if dpid in [2, 4]:  # aggregation switches
                uplink_ports = [1, 2]
                # Get the current counter for this switch
                counter = self.rr_counter[dpid]
                # Select the uplink port in a round-robin manner
                out_port = uplink_ports[counter % len(uplink_ports)]
                # Update the counter for the next flow
                self.rr_counter[dpid] += 1
                self.logger.info(f"[RR] Switch={dpid} selected uplink={out_port}")
            else:
                # For other switches, flood the packet
                out_port = ofproto.OFPP_FLOOD

        # Create action to output the packet to the selected port
        actions = [parser.OFPActionOutput(out_port)]

        # Install a flow to avoid future packet_in events for this flow
        if eth.ethertype == ether_types.ETH_TYPE_IP:
            # Match on IPv4 src and dst addresses
            # Why not IPv6? This implementation focuses on IPv4 traffic; IPv6 handling can be added similarly if needed.
            ip_pkt = pkt.get_protocol(ipv4.ipv4)
            match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP,
                                    ipv4_src=ip_pkt.src, ipv4_dst=ip_pkt.dst)
            # Why priority 1? This flow entry is for known flows and should have higher priority than table-miss entries.
            self.add_flow(datapath, 1, match, actions)
            self.logger.debug(f"[IPv4 Flow] {ip_pkt.src}->{ip_pkt.dst} via port {out_port}")

        # Send the packet out
        data = None if msg.buffer_id != ofproto.OFP_NO_BUFFER else msg.data
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)
