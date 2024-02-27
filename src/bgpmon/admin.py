from django.contrib import admin

from bgpmon.models import BGPMonitor

# Register your models here.

@admin.register(BGPMonitor)
class BGPMonitorAdmin(admin.ModelAdmin):
    list_display = (
        "instance",
        "prefix_set",
        "created",
    )
    search_fields = (
        "instance__org__name",
        "instance__org__slug",
        "prefix_set__name",
        "prefix_set__prefix_set__prefix"
    )