from django.conf import settings
from fullctl.django.settings import SettingsManager

settings_manager = SettingsManager(settings.__dict__)

# default bgpmon interval (seconds, 86400 = 1 day)
settings_manager.set_option("BGP_MONITOR_SCHEDULE_INTERVAL", 86400)