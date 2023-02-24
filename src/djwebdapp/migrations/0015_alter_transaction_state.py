# Generated by Django 4.1.5 on 2023-02-15 08:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("djwebdapp", "0014_alter_account_unique_together"),
    ]

    operations = [
        migrations.AlterField(
            model_name="transaction",
            name="state",
            field=models.CharField(
                choices=[
                    ("held", "Held"),
                    ("deleted", "Deleted during reorg"),
                    ("aborted", "Aborted"),
                    ("deploy", "To deploy"),
                    ("deploying", "Deploying"),
                    ("retry", "To retry"),
                    ("retrying", "Retrying"),
                    ("confirm", "Deployed to confirm"),
                    ("done", "Confirmed finished"),
                ],
                db_index=True,
                default="deploy",
                max_length=200,
            ),
        ),
    ]