"""
BGP Monitor logic lives here

We use IRRExplorers irrRoutes to get previous announcements and compare them to the current announcements
"""
import datetime
import ipaddress
from typing import Union

import pydantic
from django_prefixctl.models.prefixctl import ASNSet, PrefixSet
from prefix_meta.sources.irr_explorer import IRRExplorerData, IRRExplorerRequest


class BGPMonitorResultLine(pydantic.BaseModel):
    prefix: str
    type: str
    asn: int


class BGPMonitorResults(pydantic.BaseModel):
    announcements: dict[str, list[int]] = pydantic.Field(default_factory=dict)
    hijacks: dict[str, list[int]] = pydantic.Field(default_factory=dict)
    more_specifics: dict[str, list[int]] = pydantic.Field(default_factory=dict)

    @property
    def lines(self) -> list[BGPMonitorResultLine]:
        """
        Return a list of BGPMonitorResultLine objects
        """
        lines = []
        for prefix, asns in self.hijacks.items():
            for asn in asns:
                lines.append(
                    BGPMonitorResultLine(prefix=prefix, type="hijack", asn=asn)
                )
        for prefix, asns in self.more_specifics.items():
            for asn in asns:
                lines.append(
                    BGPMonitorResultLine(prefix=prefix, type="more_specific", asn=asn)
                )
        for prefix, asns in self.announcements.items():
            for asn in asns:
                lines.append(
                    BGPMonitorResultLine(prefix=prefix, type="announcement", asn=asn)
                )

        return lines

    def diff(self, other: Union["BGPMonitorResults", dict]) -> tuple:
        """
        Diff the current results with another BGPMonitorResults object
        and return the differences

        Will return a tuple of two BGPMonitorResults objects with added and removed items
        """

        if isinstance(other, dict):
            other = BGPMonitorResults(**other)

        added_announcements, removed_announcements = self._process_diff(
            "announcements", other
        )
        added_hijacks, removed_hijacks = self._process_diff("hijacks", other)
        added_more_specifics, removed_more_specifics = self._process_diff(
            "more_specifics", other
        )

        return (
            BGPMonitorResults(
                announcements=added_announcements,
                hijacks=added_hijacks,
                more_specifics=added_more_specifics,
            ),
            BGPMonitorResults(
                announcements=removed_announcements,
                hijacks=removed_hijacks,
                more_specifics=removed_more_specifics,
            ),
        )

    def _process_diff(
        self, property: str, other: "BGPMonitorResults"
    ) -> tuple[dict, dict]:
        """
        Process a diff for a given property
        """

        added = {}
        removed = {}

        for prefix, asns in getattr(self, property).items():
            if prefix not in getattr(other, property):
                added[prefix] = asns
            else:
                _asns = [
                    asn for asn in asns if asn not in getattr(other, property)[prefix]
                ]
                if _asns:
                    added[prefix] = _asns

        for prefix, asns in getattr(other, property).items():
            if prefix not in getattr(self, property):
                removed[prefix] = asns
            else:
                _asns = [
                    asn for asn in asns if asn not in getattr(self, property)[prefix]
                ]
                if _asns:
                    removed[prefix] = _asns

        return added, removed


def get_announcements(
    prefix: Union[ipaddress.IPv4Network, ipaddress.IPv6Network],
    date: datetime.datetime = None,
) -> list[int]:
    """
    Get announcements for prefix from prefixctl-meta IRRExplorerData

    Will return a list of ASNs
    """
    qset = IRRExplorerData.objects.filter(prefix=prefix)

    if date:
        qset = qset.filter(date__lte=date)

    announcements = qset.first()

    if not announcements:
        return []

    if not announcements.data:
        return []

    asns = set()

    for dataset in announcements.data:
        for irr_source in dataset.get("irrRoutes", {}):
            for route in dataset["irrRoutes"][irr_source]:
                asns.add(route["asn"])

    return sorted(list(asns))


def identify_hijacks(
    announcements: dict[str, list[int]], asn_set: ASNSet
) -> dict[str, list[int]]:
    """
    Identify hijacks in the current announcements
    """
    # identifies asns that exist in announcements but not in the asn_set

    hijacks = {}

    asn_set_asns = [asn.asn for asn in asn_set.asn_set.all()]

    for prefix, asns in announcements.items():
        hijackers = [asn for asn in asns if asn not in asn_set_asns]
        if hijackers:
            hijacks[str(prefix)] = hijackers

    return hijacks


def identify_more_specifics(
    announcements: dict[str, list[int]], prefix_set: PrefixSet
) -> dict[str, list[int]]:
    """
    Identify announcements that are more specific than the prefixes in the prefix set
    """

    more_specifics = {}

    prefixes = [prefix.prefix for prefix in prefix_set.prefix_set.all()]
    for prefix_set_prefix in prefixes:
        prefix_set_prefix = ipaddress.ip_network(prefix_set_prefix)
        for prefix, asns in announcements.items():
            prefix = ipaddress.ip_network(prefix)
            if prefix_set_prefix != prefix and prefix.subnet_of(prefix_set_prefix):
                more_specifics[str(prefix_set_prefix)] = asns

    return more_specifics


def bgp_monitor(
    prefix_set: PrefixSet,
    origin_asn_set: ASNSet,
) -> BGPMonitorResults:
    """
    Processes the BGP Monitor for a given PrefixSet

    Will return a BGPAnnouncements object with the current and previous announcements
    for all prefixes in the given PrefixSet
    """

    announcements = {}

    prefixes = list(prefix_set.prefix_set.all())

    # update announcements from IRR Explorer
    IRRExplorerRequest.request([str(prefix.prefix) for prefix in prefixes])

    # get current announcements from prefixctl-meta IRRExplorerData
    for prefix in prefixes:
        announcements[str(prefix.prefix)] = get_announcements(prefix.prefix)

    return BGPMonitorResults(
        announcements=announcements,
        hijacks=identify_hijacks(announcements, origin_asn_set),
        more_specifics=identify_more_specifics(announcements, prefix_set),
    )
