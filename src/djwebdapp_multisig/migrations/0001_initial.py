# Generated by Django 4.1.1 on 2023-01-20 16:54

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("djwebdapp_tezos", "0003_tezoscall_tezoscontract"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("djwebdapp", "0013_transaction_normalized"),
    ]

    operations = [
        migrations.CreateModel(
            name="MultisigContract",
            fields=[
                (
                    "tezostransaction_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="djwebdapp_tezos.tezostransaction",
                    ),
                ),
                (
                    "admin",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="multisigs_administered",
                        to="djwebdapp.account",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            bases=("djwebdapp_tezos.tezoscontract",),
        ),
        migrations.CreateModel(
            name="AddAuthorizedContractCall",
            fields=[
                (
                    "tezostransaction_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="djwebdapp_tezos.tezostransaction",
                    ),
                ),
                (
                    "contract_to_authorize",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="add_authorized_contract_calls",
                        to="djwebdapp_tezos.tezostransaction",
                    ),
                ),
            ],
            bases=("djwebdapp_tezos.tezoscall",),
        ),
    ]