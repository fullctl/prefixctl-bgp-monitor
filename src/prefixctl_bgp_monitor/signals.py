from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django_prefixctl.models.prefixctl import ASN, Prefix
from fullctl.django.models.concrete.tasks import TaskLimitError, TaskSchedule

from prefixctl_bgp_monitor.models import BGPMonitor, BGPMonitorTask


@receiver(post_save, sender=Prefix)
def on_prefix_create(sender, instance, created, **kwargs):
    """
    When a prefix is created, schedule a monitor task
    """
    if created:
        try:
            BGPMonitorTask.create_task(instance.prefix_set.id)
        except TaskLimitError:
            pass


@receiver(post_save, sender=ASN)
def on_asn_create(sender, instance, created, **kwargs):
    """
    When an ASN is created, schedule a monitor task
    """
    if created:
        try:
            monitor = BGPMonitor.objects.get(asn_set_origin=instance.asn_set)
            BGPMonitorTask.create_task(monitor.prefix_set.id)
        except (BGPMonitor.DoesNotExist, TaskLimitError):
            pass


@receiver(post_delete, sender=BGPMonitor)
def bgp_monitor_post_delete(sender, **kwargs):
    """
    Signal receiver for post-delete actions on a BGPMonitor.

    Deletes the associated task sceduler when the BGPMonitor is deleted.

    Arguments:
    sender: The model class that sent the signal.
    kwargs: Keyword arguments including 'instance' of the BGPMonitor being deleted.
    """
    bgp_monitor = kwargs.get("instance")

    try:
        bgp_monitor.task_schedule.delete()
    except TaskSchedule.DoesNotExist:
        pass
