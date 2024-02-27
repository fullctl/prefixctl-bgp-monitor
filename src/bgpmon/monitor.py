"""
BGP Monitor logic lives here

We use IRRExplorers irrRoutes to get previous announcements and compare them to the current announcements


[
    {
        "bgpOrigins": [
            112
        ],
        "categoryOverall": "warning",
        "goodnessOverall": 1,
        "irrRoutes": {
            "ALTDB": [
                {
                    "asn": 112,
                    "rpkiMaxLength": null,
                    "rpkiStatus": "NOT_FOUND",
                    "rpslPk": "192.175.48.0/24AS112",
                    "rpslText": "route:          192.175.48.0/24\ndescr:          Proxy-registered route object\norigin:         AS112\nremarks:        auto-generated route object\nremarks:        %%TSN-APF-R-LINEBREAK\nremarks:\nremarks:        This route is for a(n) TowardEX customer route\nremarks:        which is being exported under this origin AS.\nremarks:\nremarks:        This route object was proxy-registered by\nremarks:        MAINT-TOWARDEX because either the customer has\nremarks:        not registered the IRR objects on his own, or\nremarks:        a concern exists where some peers may be using\nremarks:        wrong database that may result in nuisance\nremarks:        filtering.\nremarks:\nremarks:        Contact irr [at] towardex.com if you have any\nremarks:        questions relating to this object.\nmnt-by:         MAINT-TOWARDEX\nchanged:        jdj@towardex.com 20051227  #TSN20051227:1552Z-26\nsource:         ALTDB\n"
                }
            ],
            "LEVEL3": [
                {
                    "asn": 112,
                    "rpkiMaxLength": null,
                    "rpkiStatus": "NOT_FOUND",
                    "rpslPk": "192.175.48.0/24AS112",
                    "rpslText": "route:          192.175.48.0/24\ndescr:          cus prefix\norigin:         AS112\nmnt-by:         MAINT-TOWARDEX\nchanged:        smc@level3.com 20140522\nsource:         LEVEL3\n"
                },
                {
                    "asn": 9942,
                    "rpkiMaxLength": null,
                    "rpkiStatus": "NOT_FOUND",
                    "rpslPk": "192.175.48.0/24AS9942",
                    "rpslText": "route:          192.175.48.0/24\ndescr:          Comindico\norigin:         AS9942\nnotify:         rw-nic@comindico.com.au\nmnt-by:         MAINT-AU-COMINDICO\nchanged:        rick.carter@comindico.com.au 20031117\nsource:         LEVEL3\n"
                }
            ],
            # ADDITIONAL IRR SOURCES ...
        }
    }
]

"""
from typing import Union
import dataclasses
import ipaddress
from django_prefixctl.models.prefixctl import PrefixSet


from prefix_meta.sources.irr_explorer import IRRExplorerRequest, IRRExplorerData

@dataclasses.dataclass
class BGPAnnouncements:
    current: dict[str, list[int]]
    previous: dict[str, list[int]]

    @property
    def has_changes(self) -> bool:
        """
        Check if there are any changes between the current and previous announcements
        """
        return self.current != self.previous

    def removed(self, prefix:Union[ipaddress.IPv4Network, ipaddress.IPv6Network]) -> list[int]:
        """
        Get ASNs that were removed from the previous announcements for a given prefix
        """
        return [asn for asn in self.previous[prefix] if asn not in self.current[prefix]]

    def added(self, prefix:Union[ipaddress.IPv4Network, ipaddress.IPv6Network]) -> list[int]:
        """
        Get ASNs that were added to the current announcements for a given prefix
        """
        return [asn for asn in self.current[prefix] if asn not in self.previous[prefix]]


def announcements(prefix:Union[ipaddress.IPv4Network, ipaddress.IPv6Network]) -> list[int]:
    """
    Get announcements for prefix from prefixctl-meta IRRExplorerData

    Will return a list of ASNs
    """
    announcements = IRRExplorerData.get_prefix_queryset(prefix).first()
    
    if not announcements:
        return []

    if not announcements.data:
        return []

    asns = set()

    for irr_source in announcements.data[0].get("irrRoutes", {}):
        for route in announcements.data[0]["irrRoutes"][irr_source]:
            asns.add(route["asn"])

    return sorted(list(asns))


def bgp_monitor(prefix_set:PrefixSet) -> BGPAnnouncements:
    
    """
    Processes the BGP Monitor for a given PrefixSet

    Will return a BGPAnnouncements object with the current and previous announcements
    for all prefixes in the given PrefixSet
    """

    _previous_announcements = {}
    _current_announcements = {}

    prefixes = list(prefix_set.prefix_set.all())

    # get previous announcements as stored in prefixctl-meta IRRExplorerData
    for prefix in prefixes:
        _previous_announcements[prefix.prefix] = announcements(prefix.prefix)
        
    # update announcements from IRR Explorer
    IRRExplorerRequest.request([str(prefix.prefix) for prefix in prefixes])

    # get current announcements from prefixctl-meta IRRExplorerData
    for prefix in prefixes:
        _current_announcements[prefix.prefix] = announcements(prefix.prefix)

    return BGPAnnouncements(
        current=_current_announcements,
        previous=_previous_announcements
    )