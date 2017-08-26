from IPy import IP

# DNS-related
class DomainList(object):
    """Tree-based domain name whitelist/blacklist/graylist. A tree structure
    is created mirroring the DNS hierarchy based on the list of domain names
    in the provided list. This tree structure is traversed to determine if a
    domain name exists in the list or not."""
    def __init__(self, whitelistfile):
        self.tree = {}
        with open(whitelistfile) as f:
            for line in f:
                lds = line.strip().split('.')
                lds.reverse()
                # Add to tree data structure
                node = self.tree
                for ld in lds:
                    if ld not in node:
                        node[ld] = {}
                    node = node[ld]

                # Sentinel to prove this node can be considered a leaf. This
                # allows subdomains to be included in the whitelist file.
                node[1] = True

    def __contains__(self, domain):
        lds = domain.split('.')
        lds.reverse()
        node = self.tree
        try:
            for ld in lds:
                node = node[ld]
        # This will (almost) always happen unless the domain is an exact
        # match for one in the domain list (e.g., 'google.com').
        except KeyError:
            pass

        # If 1 in node is True, we've found a leaf node.
        return 1 in node

class IPList(object):
    """IP/CIDR whitelist/blacklist/greylist. A sorted list of networks is
    created from the provided networks and a binary search is performed to see
    if the provided IP exists in the list of networks. If a list of IPs is given
    one can optionally provide a network size to expand the IPs to. For all
    networks in the list, none must be a subset of any other networks in the
    list. See the comment in __init__() for a further explanation."""

    def __init__(self, iplistfile, netsize=None):
        self.networks = []
        with open(iplistfile) as f:
            for line in f:
                if netsize is None:
                    self.networks.append(self.IP(line.strip()))
                else:
                    ip = line.strip()
                    # Make a network for the given IP at the provided netsize
                    net = self.IP(ip).make_net(self.IP((2 << netsize - 1) - 1))
                    self.networks.append(net)

        self.networks = sorted(self.networks, key=lambda x: x.int())
        for i, net1 in enumerate(self.networks):
            for net2 in self.networks[i+1:]:
                try:
                    # Networks can overlap in a way that breaks the correctness
                    # of how I compute __contains__. For example:
                    # >>> bogons = IPList('somefile')
                    # >>> bogons.networks = sorted([IP('41.0.0.0/8'), IP('41.41.0.0/24'), IP('41.255.0.0/16')], key=lambda x: x.int())
                    # >>> '41.100.0.0' in bogons
                    # False
                    #
                    # This is obviously incorrect, and is due to the fact that
                    # the middle network is contained within the first network.
                    # When the provided IP is "larger" than the middle network,
                    # it incorrectly chooses the upper half as the next step in
                    # the recursion. To prevent this from happening, we throw a
                    # ValueError if this condition exists in the list. For what
                    # I'm doing right now, this isn't a problem but it may cause
                    # problems in the future.
                    assert(net1[-1].int() <= net2[-1].int())
                except AssertionError:
                    raise ValueError('%s is contained within %s!' % (net2, net1))

    def _find(self, networks, ip):
        mid = len(networks) / 2
        try:
            net = networks[mid]
        except IndexError: # Not in list
            return False
        if ip in net:
            return net
        elif self.IP(ip).int() > net.int():
            return self._find(networks[mid+1:], ip)
        else:
            return self._find(networks[:mid], ip)

    def __contains__(self, ip):
        return self._find(self.networks, ip)
