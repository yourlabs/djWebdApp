# Generated by Django 4.1.1 on 2023-02-03 14:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("djwebdapp", "0012_transaction_number"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="normalized",
            field=models.BooleanField(
                default=False, help_text="Enabled when transaction is normalized"
            ),
        ),
        migrations.CreateModel(
            name="Dependency",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                (
                    "dependency",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dependent_set",
                        to="djwebdapp.transaction",
                    ),
                ),
                (
                    "dependent",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="djwebdapp.transaction",
                    ),
                ),
                (
                    "graph",
                    models.ForeignKey(
                        help_text="The transaction this graph was created for",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="graph",
                        to="djwebdapp.transaction",
                    ),
                ),
            ],
        ),
    ]
