from django.apps import AppConfig


class BgpmonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "bgpmon"

    def ready(self):
        import bgpmon.settings # noqa
        import bgpmon.serializers # noqa