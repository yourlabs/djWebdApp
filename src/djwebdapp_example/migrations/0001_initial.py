# Generated by Django 4.0.1 on 2022-02-19 19:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('djwebdapp_tezos', '0001_initial'),
        ('djwebdapp', '0001_initial'),
        ('djwebdapp_ethereum', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FA12',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=200, null=True)),
                ('symbol', models.CharField(blank=True, max_length=10, null=True)),
                ('ethereum_contract', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='djwebdapp_ethereum.ethereumtransaction')),
                ('tezos_contract', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='djwebdapp_tezos.tezostransaction')),
            ],
        ),
        migrations.CreateModel(
            name='Mint',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.PositiveIntegerField()),
                ('address', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='djwebdapp.account')),
                ('ethereum_call', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='djwebdapp_ethereum.ethereumtransaction')),
                ('fa12', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='djwebdapp_example.fa12')),
                ('tezos_call', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='djwebdapp_tezos.tezostransaction')),
            ],
        ),
        migrations.CreateModel(
            name='Balance',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('balance', models.PositiveIntegerField()),
                ('address', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fa12_balance_set', to='djwebdapp.account')),
                ('fa12', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='djwebdapp_example.fa12')),
            ],
            options={
                'unique_together': {('fa12', 'address')},
            },
        ),
    ]
