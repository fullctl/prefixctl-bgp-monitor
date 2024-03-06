from django_prefixctl.rest.decorators import grainy_endpoint
from django_prefixctl.rest.route.prefixctl import route
from fullctl.django.rest.mixins import OrgQuerysetMixin
from rest_framework import viewsets
from rest_framework.response import Response

import prefixctl_bgp_monitor.models as models
from prefixctl_bgp_monitor.monitor import BGPMonitorResults
from prefixctl_bgp_monitor.serializers import Serializers


@route
class BGPMonitorReport(OrgQuerysetMixin, viewsets.GenericViewSet):

    """
    BGP Monitor REST API
    """

    ref_tag = "bgp_monitor/report"

    queryset = models.BGPMonitor.objects.all()
    serializer_class = Serializers.report

    @grainy_endpoint(namespace="prefix_monitor.{request.org.permission_id}")
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve the BGP announcements for a given monitor
        """

        monitor = self.get_object()
        result = BGPMonitorResults(**monitor.result)

        return Response(self.get_serializer(result.lines).data)
