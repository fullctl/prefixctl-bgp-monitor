from typing import Union
from django.db import models
from django.conf import settings
from django_grainy.decorators import grainy_model
from fullctl.django.models import Task, TaskSchedule, Instance
from fullctl.django.tasks import register as register_task

from django_prefixctl.models import PrefixSet, register_prefix_monitor, Monitor

from bgpmon.monitor import bgp_monitor

PERMISSION_NAMESPACE = "bgpmon"
PERMISSION_NAMESPACE_INSTANCE = "bgpmon.{instance.instance.org.permission_id}"

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

    # task scheduler
    task_schedule = models.OneToOneField(
        TaskSchedule,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="The task schedule for this monitor",
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
        return PrefixSet.objects.get(id=self.prefix_set_id)

    @property
    def generate_limit_id(self) -> Union[str, int]:
        """
        Helper function to generate the limit id for the task worker.

        In this case we just want to limit the instances of this task running for a given prefix set.
        """
        return self.prefix_set_id

    def run(self, *args, **kwargs):
        """
        The run method is called by the task worker.

        Arguments:

        - args: A list of arguments passed to the task through `create_task`
        - kwargs: A dictionary of keyword arguments passed to the task through `create_task`
        """
        self.output = bgp_monitor(self.prefix_set)
        return self.output