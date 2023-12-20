# Generated by Django 4.2.7 on 2023-11-28 17:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("djwebdapp", "0017_event"),
        ("djwebdapp_ethereum", "0004_ethereumevent"),
        ("djwebdapp_example_ethereum", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="FA12EthereumBalanceMovement",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("amount", models.PositiveIntegerField(default=0)),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="djwebdapp.account",
                    ),
                ),
                (
                    "event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fa12_balance_movements",
                        to="djwebdapp_ethereum.ethereumevent",
                    ),
                ),
                (
                    "fa12",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="djwebdapp_example_ethereum.fa12ethereum",
                    ),
                ),
            ],
        ),
    ]
