from typing import Type

from django.core.cache import cache
from django.db.models.signals import post_save
from django.dispatch import receiver

from sentry.models.project import Project
from sentry.monitors.models import MonitorEnvironment
from sentry.tasks.relay import schedule_invalidate_project_config

# Determines how many check-ins per-minute will be allowed per monitor. This is
# used when computing the QuotaConfig for the DataCategory.MONITOR (check-ins)
#
#
# Each monitor should __really__ only be checking-in once per minute, but we
# will give some lee-way to allow for customers whos monitors check-in early.
ALLOWED_CHECK_INS_PER_MONITOR_PER_MINUTE = 5

# The minimum computed project_monitor_rate_limit. This value should be high
# enough that it allows for a large number of monitors to be upserted without
# hitting the project rate-limit.
ALLOWED_MINIMUM = 50


def get_project_monitor_rate_limit(project: Project, cache_bust=False) -> int:
    """
    Determines the rate-limit for monitor check-ins across a particular
    project.

    This value is intended to be used with a 10 minute window.

    The rate limit is computed as a per project limit. This means the total
    number of check-ins allowed per-projects is computed as follows

    >>> total_monitor_environments * ALLOWED_CHECK_INS_PER_MONITOR_PER_MINUTE
    """
    limit = None
    cache_key = f"project:{project.id}:monitor-env-count"

    # Cache rate-limit computation. This function will be called often by the
    # Quotas system.
    if not cache_bust:
        limit = cache.get(cache_key)

    if limit is None:
        monitor_count = MonitorEnvironment.objects.filter(monitor__project_id=project.id).count()
        limit = monitor_count * ALLOWED_CHECK_INS_PER_MONITOR_PER_MINUTE
        cache.set(cache_key, limit, 600)

    return max(limit, ALLOWED_MINIMUM)


@receiver(post_save, sender=MonitorEnvironment)
def update_monitor_rate_limit(
    sender: Type[MonitorEnvironment],
    instance: MonitorEnvironment,
    created: bool,
    **kwargs,
):
    """
    When new monitor environments are created we recompute the per-project
    monitor check-in rate limit QuotaConfig in relay.
    """
    if not created:
        return

    project = instance.monitor.project

    get_project_monitor_rate_limit(project, cache_bust=True)
    schedule_invalidate_project_config(
        project_id=project.id,
        trigger="monitors:monitor_created",
    )
