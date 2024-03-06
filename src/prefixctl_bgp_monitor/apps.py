from django.apps import AppConfig


class PrefixCtlBGPMonitorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "prefixctl_bgp_monitor"

    def ready(self):
        import prefixctl_bgp_monitor.settings  # noqa
        import prefixctl_bgp_monitor.serializers  # noqa
        import prefixctl_bgp_monitor.views  # noqa
        import prefixctl_bgp_monitor.signals  # noqa
