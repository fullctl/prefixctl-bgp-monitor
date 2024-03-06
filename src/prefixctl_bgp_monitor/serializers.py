from django_prefixctl.rest.serializers.monitor import (
    MonitorCreationMixin,
    register_prefix_monitor,
)
from fullctl.django.rest.decorators import serializer_registry
from fullctl.django.rest.serializers import ModelSerializer
from rest_framework import serializers

import prefixctl_bgp_monitor.models as models

Serializers, register = serializer_registry()


# register the monitor with prefixctl
@register_prefix_monitor
# add the monitor to the serializer registry, afterwards it
# will be available as Serializers.bgp_monitor, purely for convenience
@register
class BGPMonitor(MonitorCreationMixin, ModelSerializer):

    """
    A bare minimum monitor REST serializer for the BGP Monitor.
    """

    # set the monitor type choices and default
    # to the reference tag of the monitor model
    monitor_type = serializers.ChoiceField(
        choices=["bgp_monitor"], default="bgp_monitor"
    )
    instance = serializers.PrimaryKeyRelatedField(read_only=True)
    email = serializers.EmailField(required=False)

    class Meta:
        model = models.BGPMonitor
        fields = [
            "instance",
            "prefix_set",
            "asn_set_origin",
            "alert_specifics",
            "monitor_type",
            "email",
            "result",
        ]


class BGPMonitorReportLine(serializers.Serializer):
    prefix = serializers.CharField()
    asn = serializers.IntegerField()
    type = serializers.CharField()

    class Meta:
        fields = ["prefix", "asns", "type"]


@register
class BGPMonitorReport(serializers.ListSerializer):
    ref_tag = "report"
    child = BGPMonitorReportLine()
