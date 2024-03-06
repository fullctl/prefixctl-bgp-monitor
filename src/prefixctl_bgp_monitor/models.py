from typing import Union

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_grainy.decorators import grainy_model
from django_prefixctl.models import ASNSet, Monitor, PrefixSet, register_prefix_monitor
from fullctl.django.mail import send_plain
from fullctl.django.models import Instance, Task, TaskSchedule
from fullctl.django.tasks import register as register_task

from prefixctl_bgp_monitor.monitor import BGPMonitorResults, bgp_monitor

PERMISSION_NAMESPACE = "prefix_monitor"
PERMISSION_NAMESPACE_INSTANCE = "prefix_monitor.{instance.instance.org.permission_id}"


@register_prefix_monitor
@grainy_model(PERMISSION_NAMESPACE, namespace_instance=PERMISSION_NAMESPACE_INSTANCE)
class BGPMonitor(Monitor):

    """
    Describes per prefix-set instance of your monitor.
    """

    # organization workspace intance
    instance = models.ForeignKey(
        Instance, related_name="bgp_monitors", on_delete=models.CASCADE
    )

    # the prefix set that the monitor is running for
    prefix_set = models.OneToOneField(
        PrefixSet, related_name="bgp_monitors", on_delete=models.CASCADE
    )

    # the origin ASN set
    asn_set_origin = models.ForeignKey(
        ASNSet, related_name="prefix_monitor_origin_set", on_delete=models.CASCADE
    )

    # task scheduler
    task_schedule = models.OneToOneField(
        TaskSchedule,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="The task schedule for this monitor",
    )

    email = models.EmailField(
        null=True,
        blank=True,
        help_text="Email address to send notifications to",
    )

    alert_specifics = models.BooleanField(help_text=_("Alert on more specifics"))

    checked = models.DateTimeField(
        null=True,
        blank=True,
        help_text="The last time the monitor was checked",
    )

    result = models.JSONField(
        null=True,
        blank=True,
        help_text="The last result of the monitor",
    )

    class Meta:
        db_table = "prefixctl_bgp_monitor"
        verbose_name = "BGP Monitor"
        verbose_name_plural = "BGP Monitors"

    class HandleRef:
        tag = "bgp_monitor"

    @property
    def schedule_interval(self):
        """
        The schedule interval for the task worker.
        """
        return settings.BGP_MONITOR_SCHEDULE_INTERVAL

    @property
    def schedule_task_config(self):
        """
        Task schedule configuration
        """
        return {
            "tasks": [
                {
                    # the task worker class HandleRef tag
                    # which we used to register the BGPMonitorTask class
                    "op": "bgp_monitor_task",
                    # create_task arguments
                    "param": {
                        # in this case we are just passing the prefix set id
                        "args": [self.prefix_set.id],
                    },
                }
            ]
        }


# TASK WORKER MODEL


# Task worker models need to be registered with fullctl so they
# are available to the task worker.
@register_task
class BGPMonitorTask(Task):

    """
    A task worker model.

    This is a proxied model running on the same table as the fullctl
    Task base.

    Additional documentation on fullctl task classes can be found at:

    https://github.com/fullctl/fullctl/blob/main/docs/tasks.md

    This is were the logic of your monitor is executed.

    `create_task` arguments:
        - prefix_set_id: int - The PrefixSet model instance id that the monitor is running for.
    """

    class Meta:
        proxy = True

    class HandleRef:
        # a unique identifier for the task
        tag = "bgp_monitor_task"

    class TaskMeta:
        # only one instance per limiter is allowed to run at a time
        # the limiter valus is defined via the generate_limit_id property
        limit = 1

    @property
    def prefix_set_id(self) -> int:
        """
        Helper function to get the prefix set id from the create_task arguments.
        """
        return self.param["args"][0]

    @property
    def prefix_set(self) -> PrefixSet:
        """
        Helper function to get the prefix set model instance from the create_task arguments.
        """
        if not hasattr(self, "_prefix_set"):
            self._prefix_set = PrefixSet.objects.get(id=self.prefix_set_id)
        return self._prefix_set

    @property
    def generate_limit_id(self) -> Union[str, int]:
        """
        Helper function to generate the limit id for the task worker.

        In this case we just want to limit the instances of this task running for a given prefix set.
        """
        return self.prefix_set_id

    @property
    def monitor(self) -> BGPMonitor:
        """
        Helper function to get the monitor model instance from the create_task arguments.
        """
        if not hasattr(self, "_monitor"):
            self._monitor = BGPMonitor.objects.get(prefix_set=self.prefix_set)
        return self._monitor

    def run(self, *args, **kwargs):
        """
        The run method is called by the task worker.

        Arguments:

        - args: A list of arguments passed to the task through `create_task`
        - kwargs: A dictionary of keyword arguments passed to the task through `create_task`
        """

        prev_result = self.monitor.result

        results = bgp_monitor(
            self.prefix_set,
            self.monitor.asn_set_origin,
        )

        self.monitor.checked = timezone.now()
        self.monitor.result = results.model_dump()
        self.monitor.save()

        self.output = results.model_dump_json(indent=2)

        if prev_result:
            added, removed = results.diff(prev_result)
            self.notify(added, removed)
        else:
            self.notify(results, BGPMonitorResults())

        return self.output

    def formatted_asns(self, asns):
        _asns = []
        for asn in sorted(asns):
            _asns.append(f"- AS{asn}")
        return "\n".join(_asns)

    def notify(self, added: BGPMonitorResults, removed: BGPMonitorResults):
        if not self.monitor.email:
            return

        hijack_changes = added.hijacks or removed.hijacks
        more_specifics_changes = added.more_specifics or removed.more_specifics

        if not hijack_changes and not more_specifics_changes:
            return

        subject = "BGP Monitor Notification"

        message = f"Monitor {self.monitor.prefix_set.name} has detected changes:\n\n"

        for prefix, asns in added.hijacks.items():
            message += f"Prefix {prefix} is being BGP hijacked by:\n{self.formatted_asns(asns)}\n\n"

        for prefix, asns in removed.hijacks.items():
            message += f"Prefix {prefix} no longer being BGP hijacked by:\n{self.formatted_asns(asns)}\n\n"

        if self.monitor.alert_specifics:
            for prefix, asns in added.more_specifics.items():
                message += f"Prefix {prefix} has new more specific announcements:\n{self.formatted_asns(asns)}\n\n"

            for prefix, asns in removed.more_specifics.items():
                message += f"Prefix {prefix} no longer has these more specific announcements:\n{self.formatted_asns(asns)}\n\n"

        send_plain(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [self.monitor.email],
        )
