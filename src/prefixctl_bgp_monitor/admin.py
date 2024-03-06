from django.contrib import admin

from prefixctl_bgp_monitor.models import BGPMonitor

# Register your models here.


@admin.register(BGPMonitor)
class BGPMonitorAdmin(admin.ModelAdmin):
    list_display = (
        "instance",
        "prefix_set",
        "asn_set_origin",
        "alert_specifics",
        "created",
        "checked",
    )
    search_fields = (
        "instance__org__name",
        "instance__org__slug",
        "asn_set_origin__name",
        "prefix_set__name",
        "prefix_set__prefix_set__prefix",
    )
    autocomplete_fields = ("prefix_set", "asn_set_origin")
