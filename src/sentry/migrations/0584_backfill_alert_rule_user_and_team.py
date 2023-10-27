# Generated by Django 2.2.28 on 2023-04-26 19:54

from django.db import migrations

from sentry.new_migrations.migrations import CheckedMigration
from sentry.utils.query import RangeQuerySetWrapperWithProgressBar


def backfill_alert_rule_user_and_team(apps, schema_editor):
    AlertRule = apps.get_model("sentry", "AlertRule")
    for ar in RangeQuerySetWrapperWithProgressBar(AlertRule.objects.all().select_related("owner")):
        if ar.owner:
            ar.user_id = ar.owner.user_id
            ar.team_id = ar.owner.team_id
            ar.save(updated_fields=["user_id", "team_id"])


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
    is_dangerous = True

    dependencies = [
        ("sentry", "0583_add_early_adopter_to_organization_mapping"),
    ]

    operations = [
        migrations.RunPython(
            backfill_alert_rule_user_and_team,
            reverse_code=migrations.RunPython.noop,
            hints={"tables": ["sentry_alertrule"]},
        ),
    ]
