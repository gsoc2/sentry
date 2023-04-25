# Generated by Django 2.2.28 on 2023-04-25 22:40

from django.db import connection, migrations
from psycopg2.extras import execute_values

from sentry.models import GroupStatus, GroupSubStatus
from sentry.new_migrations.migrations import CheckedMigration
from sentry.utils.query import RangeQuerySetWrapper

BATCH_SIZE = 100

UPDATE_QUERY = """
    UPDATE sentry_groupedmessage
    SET substatus = %s
    FROM (VALUES %s) as data (id)
    WHERE sentry_groupedmessage.id = data.id
"""


def backfill_substatus(apps, schema_editor):
    Group = apps.get_model("sentry", "Group")
    GroupSnooze = apps.get_model("sentry", "GroupSnooze")

    cursor = connection.cursor()
    archived_forever_batch = []
    archived_until_condition_met_batch = []

    for group_id, status, substatus in RangeQuerySetWrapper(
        Group.objects.all().values_list("id", "status", "substatus"),
        result_value_getter=lambda item: item[0],
    ):
        if status is not GroupStatus.IGNORED:
            continue

        group_snooze = GroupSnooze.objects.filter(group_id=group_id)

        if not group_snooze:
            archived_forever_batch.append((group_id, GroupSubStatus.FOREVER))
        if substatus is not None:
            archived_until_condition_met_batch.append(
                (group_id, GroupSubStatus.UNTIL_CONDITION_MET)
            )

        if len(archived_forever_batch) >= BATCH_SIZE:
            execute_values(
                cursor,
                UPDATE_QUERY,
                GroupSubStatus.FOREVER,
                archived_forever_batch,
                page_size=BATCH_SIZE,
            )
            archived_forever_batch = []

        if len(archived_until_condition_met_batch) >= BATCH_SIZE:
            execute_values(
                cursor,
                UPDATE_QUERY,
                GroupSubStatus.UNTIL_CONDITION_MET,
                archived_until_condition_met_batch,
                page_size=BATCH_SIZE,
            )
            archived_until_condition_met_batch = []

    if archived_forever_batch:
        execute_values(
            cursor,
            UPDATE_QUERY,
            GroupSubStatus.FOREVER,
            archived_forever_batch,
            page_size=BATCH_SIZE,
        )

    if archived_until_condition_met_batch:
        execute_values(
            cursor,
            UPDATE_QUERY,
            GroupSubStatus.UNTIL_CONDITION_MET,
            archived_until_condition_met_batch,
            page_size=BATCH_SIZE,
        )


class Migration(CheckedMigration):
    # This flag is used to mark that a migration shouldn't be automatically run in production. For
    # the most part, this should only be used for operations where it's safe to run the migration
    # after your code has deployed. So this should not be used for most operations that alter the
    # schema of a table.
    # Here are some things that make sense to mark as dangerous:
    # - Large data migrations. Typically we want these to be run manually by ops so that they can
    #   be monitored and not block the deploy for a long period of time while they run.
    # - Adding indexes to large tables. Since this can take a long time, we'd generally prefer to
    #   have ops run this and not block the deploy. Note that while adding an index is a schema
    #   change, it's completely safe to run the operation after the code has deployed.
    is_dangerous = False

    dependencies = [
        ("sentry", "0428_backfill_denormalize_notification_actor"),
    ]

    operations = [
        migrations.RunPython(
            backfill_substatus,
            reverse_code=migrations.RunPython.noop,
            hints={"tables": ["sentry_groupedmessage", "sentry_groupsnooze"]},
        ),
    ]
