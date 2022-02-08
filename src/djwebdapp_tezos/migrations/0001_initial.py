# Generated by Django 3.1.14 on 2022-02-09 17:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('djwebdapp', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TezosTransaction',
            fields=[
                ('transaction_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='djwebdapp.transaction')),
                ('micheline', models.JSONField(blank=True, default=dict, help_text='Smart contract Micheline, if this is a smart contract', null=True)),
                ('contract', models.ForeignKey(blank=True, help_text='Smart contract, appliable to method call', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='call_set', to='djwebdapp_tezos.tezostransaction')),
            ],
            bases=('djwebdapp.transaction',),
        ),
    ]