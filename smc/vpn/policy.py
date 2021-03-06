from smc.base.model import Element, ElementCreator, SubElement
from smc.api.exceptions import CreatePolicyFailed, CreateElementFailed,\
    PolicyCommandFailed, ElementNotFound
from smc.base.collection import sub_collection
from smc.vpn.elements import VPNProfile


class PolicyVPN(Element):
    """
    Create a new VPN Policy.
    ::
    
        >>> PolicyVPN.create(name='myvpn')
        PolicyVPN(name=myvpn)
        >>> v = PolicyVPN('myvpn')
        >>> print(v.vpn_profile)
        VPNProfile(name=VPN-A Suite)

    When making VPN Policy modifications, you must first call :func:`open`, 
    make your modifications and then call :func:`save` followed by 
    :func:`close`.
    """
    typeof = 'vpn'

    def __init__(self, name, **meta):
        super(PolicyVPN, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls, name, nat=False, mobile_vpn_toplogy_mode=None,
               vpn_profile=None):
        """
        Create a new policy based VPN

        :param name: name of vpn policy
        :param bool nat: whether to apply NAT to the VPN (default False)
        :param mobile_vpn_toplogy_mode: whether to allow remote vpn
        :param VPNProfile vpn_profile: reference to VPN profile, or uses default
        :rtype: PolicyVPN
        """
        vpn_profile = vpn_profile if vpn_profile else VPNProfile('VPN-A Suite')
        
        json = {'mobile_vpn_topology_mode': mobile_vpn_toplogy_mode,
                'name': name,
                'nat': nat,
                'vpn_profile': vpn_profile.href}

        try:
            return ElementCreator(cls, json)
        except CreateElementFailed as err:
            raise CreatePolicyFailed(err)

    @property
    def nat(self):
        """ 
        Is NAT enabled on this vpn policy

        :return: NAT enabled
        :rtype: bool
        """
        return self.data.get('nat')

    def enable_disable_nat(self):
        """
        Enable or disable NAT on this policy. If NAT is disabled, it
        will be enabled and vice versa.

        :return: None
        """
        if self.nat:
            self.data['nat'] = False
        else:
            self.data['nat'] = True

    @property
    def vpn_profile(self):
        """
        Specified VPN Profile used by this VPN Policy

        :return: :class:`smc.vpn.elements.VPNProfile`
        """
        return Element.from_href(self.data.get('vpn_profile'))

    @property
    def central_gateway_node(self):
        """
        Central Gateway Node acts as the hub of a hub-spoke VPN. 

        :return: collection of :class:`GatewayNode`
        :rtype: SubElementCollection
        """
        return sub_collection(
            self.data.get_link('central_gateway_node'),
            type('CentralGatewayNode', (GatewayNode,), {}))

    @property
    def satellite_gateway_node(self):
        """
        Node level settings for configured satellite gateways

        :return: collection of :class:`GatewayNode`
        :rtype: SubElementCollection
        """
        return sub_collection(
            self.data.get_link('satellite_gateway_node'),
            type('SatelliteGatewayNode', (GatewayNode,), {}))

    @property
    def mobile_gateway_node(self):
        """
        Mobile Gateway's are represented by client endpoints connecting
        to the policy based VPN.

        :return: collection of :class:`GatewayNode`
        :rtype: SubElementCollection
        """
        return sub_collection(
            self.data.get_link('mobile_gateway_node'),
            type('MobileGatewayNode', (GatewayNode,), {}))

    def open(self):
        """
        Open the policy for editing

        :return: None
        :raises PolicyCommandFailed: couldn't open policy with reason
        """
        self.send_cmd(
            PolicyCommandFailed,
            resource='open')

    def save(self):
        """
        Save the policy after editing

        :return: None
        :raises PolicyCommandFailed: save failed with reason
        """
        self.send_cmd(
            PolicyCommandFailed,
            resource='save')

    def close(self):
        """
        Close the policy 

        :raises PolicyCommandFailed: close failed with reason
        :return: None
        """
        self.send_cmd(
            PolicyCommandFailed,
            resource='close')

    def validate(self):
        """
        Return a validation string from the SMC after running validate on
        this VPN policy.
        
        :return: status as string
        :rtype: str
        """
        return self.read_cmd(
            resource='validate').get('value')

    def gateway_tunnel(self):
        """
        """
        return self.read_cmd(
            resource='gateway_tunnel')

    def add_central_gateway(self, gateway):
        """ 
        Add SMC managed internal gateway to the Central Gateways of this VPN

        :param gateway: href for internal gateway or test_external gateway.
               If this is another SMC managed gateway, you can retrieve the 
               href after loading the engine. 
               See :py:class:`smc.core.engines.Engine.internal_gateway`
        :raises PolicyCommandFailed: could not add gateway
        :return: None
        """
        self.send_cmd(
            PolicyCommandFailed,
            resource='central_gateway_node',
            json={'gateway': gateway,
                  'node_usage': 'central'})

    def add_satellite_gateway(self, gateway):
        """
        Add gateway node as a satellite gateway for this VPN. You must first
        have the gateway object created. This is typically used when you either 
        want a hub-and-spoke topology or the test_external gateway is a non-SMC 
        managed device.

        :param gateway: href for internal gateway or test_external gateway.
               If this is another SMC managed gateway, you can retrieve the 
               href after loading the engine. 
               See :py:class:`smc.core.engines.Engine.internal_gateway` 
        :raises PolicyCommandFailed: could not add gateway
        :return: None
        """
        self.send_cmd(
            PolicyCommandFailed,
            resource='satellite_gateway_node',
            json={'gateway': gateway,
                  'node_usage': 'satellite'})

    @staticmethod
    def add_internal_gateway_to_vpn(internal_gateway_href, vpn_policy,
                                    vpn_role='central'):
        """
        Add an internal gateway (managed engine node) to a VPN policy
        based on the internal gateway href.

        :param str internal_gateway_href: href for engine internal gw
        :param str vpn_policy: name of vpn policy
        :param str vpn_role: central|satellite
        :return: True for success
        :rtype: bool
        """
        try:
            vpn = PolicyVPN(vpn_policy)
            vpn.open()
            if vpn_role == 'central':
                vpn.add_central_gateway(internal_gateway_href)
            else:
                vpn.add_satellite_gateway(internal_gateway_href)
            vpn.save()
            vpn.close()
        except ElementNotFound:
            return False
        return True


class GatewayNode(SubElement):
    """
    Top level VPN gateway node operations. A gateway node is characterized
    by a Central Gateway, Satellite Gateway or Mobile Gateway node.
    This template class will return these as a collection. Gateway Node
    references need to be obtained from a VPN Policy reference::

        >>> vpn = PolicyVPN('sg_vm_vpn')
        >>> vpn.open()
        >>> for gw in vpn.central_gateway_node.all():
        ...   list(gw.enabled_sites)
        ... 
        [GatewayTreeNode(name=Automatic Site for sg_vm_vpn)]
        >>> vpn.close()
    """

    def __init__(self, **meta):
        super(GatewayNode, self).__init__(**meta)
        pass

    @property
    def name(self):
        """
        Get the name from the gateway_profile reference
        """
        return Element.from_href(self.data['gateway']).name
    
    @property
    def enabled_sites(self):
        """
        Return a collection of VPN Site elements that are enabled
        for this VPN gateway.

        :return: collection of :class:`smc.vpn.elements.VPNSite`
        :rtype: SubElementCollection
        """
        return sub_collection(
            self.data.get_link('enabled_vpn_site'), GatewayTreeNode)

    @property
    def disabled_sites(self):
        """
        Return a collection of VPN Site elements that are disabled
        for this VPN gateway.

        :return: collection of :class:`smc.vpn.elements.VPNSite`
        :rtype: SubElementCollection
        """
        return sub_collection(
            self.data.get_link('disabled_vpn_site'), GatewayTreeNode)

class GatewayTreeNode(SubElement):
    """
    Gateway Tree node is a list of VPN Site elements returned when retrieving
    a VPN policies enabled or disabled site list. These provide an
    enable_disable link to the VPN site.
    ::
    
        for gw in policy.central_gateway_node.all():
            for site in list(gw.enabled_sites):
                site.enable_disable()
    """
    @property
    def name(self):
        return self.vpn_site.name
    
    """
    A gateway tree node is a VPN site within either the central or 
    satellite gateway configuration within a VPN.
    """
    def enable_disable(self):
        """
        Enable or disable this VPN Site from within the VPN policy context.
        
        :raises PolicyCommandFailed: enabling or disabling failed
        :return: None
        """
        self.del_cmd(
            PolicyCommandFailed,
            resource='self')
    
    @property
    def vpn_site(self):
        """
        The VPN Site element associated with this gateway
        
        :return VPNSite element
        :rtype: VPNSite
        """
        return Element.from_href(self.data.get('vpn_site'))
    
    def __str__(self):
        return '{0}(name={1})'.format(
            self.__class__.__name__, self.name)

    def __repr__(self):
        return str(self)
            