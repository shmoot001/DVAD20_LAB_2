from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types, arp, ipv4


class RoundRobinLB(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(RoundRobinLB, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.rr_counter = {}
        self.logger.info("[Init] RoundRobinLB controller started")

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match, instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)
        self.logger.info(f"[FlowInstall] switch={datapath.id}, match={match}, actions={actions}, priority={priority}")

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        self.logger.info(f"[SwitchFeatures] Switch {datapath.id} connected")

        # Default rule: send everything to controller
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

        self.rr_counter[datapath.id] = 0
        self.logger.info(f"[RR Init] Counter for switch {datapath.id} set to 0")

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            self.logger.debug("[PacketIn] Ignoring LLDP packet")
            return

        dst, src = eth.dst, eth.src
        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        self.logger.info(f"[PacketIn] switch={dpid}, in_port={in_port}, src={src}, dst={dst}, eth_type={hex(eth.ethertype)}")

        # MAC learning
        self.mac_to_port[dpid][src] = in_port
        self.logger.info(f"[MAC Learning] Learned {src} -> port {in_port} on switch {dpid}")

        # Decide output port
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
            self.logger.info(f"[Forwarding] Known dst={dst}, out_port={out_port}")
        else:
            if dpid in [2, 4]:  # Aggregation switches
                uplink_ports = [1, 2]
                counter = self.rr_counter[dpid]
                out_port = uplink_ports[counter % len(uplink_ports)]
                self.rr_counter[dpid] += 1
                self.logger.info(f"[RR Decision] switch={dpid}, counter={counter}, out_port={out_port}")
            else:
                out_port = ofproto.OFPP_FLOOD
                self.logger.info(f"[Flood] Unknown dst={dst}, flooding on switch={dpid}")

        actions = [parser.OFPActionOutput(out_port)]

        # Install flows
        if eth.ethertype == ether_types.ETH_TYPE_IP:
            ip_pkt = pkt.get_protocol(ipv4.ipv4)
            match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP,
                                    ipv4_src=ip_pkt.src, ipv4_dst=ip_pkt.dst)
            self.add_flow(datapath, 1, match, actions)

        if eth.ethertype == ether_types.ETH_TYPE_ARP:
            arp_pkt = pkt.get_protocol(arp.arp)
            match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_ARP,
                                    arp_spa=arp_pkt.src_ip, arp_tpa=arp_pkt.dst_ip)
            self.add_flow(datapath, 1, match, actions)

        # Send packet out
        data = None if msg.buffer_id != ofproto.OFP_NO_BUFFER else msg.data
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)
        self.logger.info(f"[PacketOut] switch={dpid}, out_port={out_port}, src={src}, dst={dst}")
