# Generated by Django 3.1.14 on 2021-12-23 23:33

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Address',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=100, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True, null=True)),
                ('address', models.CharField(blank=True, max_length=255, null=True)),
                ('balance', models.DecimalField(blank=True, decimal_places=9, default=0, editable=False, max_digits=18)),
            ],
        ),
        migrations.CreateModel(
            name='Blockchain',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('provider_class', models.CharField(choices=[('djwebdapp_tezos.Provider', 'Tezos'), ('djwebdapp.provider.Success', 'Test that always succeeds'), ('djwebdapp.provider.FailDeploy', 'Test that fails deploy'), ('djwebdapp.provider.FailWatch', 'Test that fails watch')], max_length=255)),
                ('is_active', models.BooleanField(default=True, help_text='Check to activate this blockchain')),
                ('description', models.TextField(blank=True, help_text='Free text to describe the blockchain to users')),
                ('unit', models.CharField(help_text='Unit name, ie. btc, xtz...', max_length=15)),
                ('unit_micro', models.CharField(help_text='Unit name, ie. satoshi, mutez...', max_length=15)),
                ('max_level', models.PositiveIntegerField(blank=True, default=None, help_text='Highest indexed level', null=True)),
                ('min_level', models.PositiveIntegerField(blank=True, default=None, help_text='Lowest indexed level', null=True)),
                ('confirmation_blocks', models.IntegerField(default=0, help_text='Number of blocks before considering a transaction written')),
                ('configuration', models.JSONField(blank=True, default=dict)),
            ],
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True, null=True)),
                ('name', models.CharField(blank=True, help_text='Free label', max_length=100, null=True)),
                ('description', models.TextField(blank=True, help_text='Free description text', null=True)),
                ('datetime', models.DateTimeField(auto_now=True, null=True)),
                ('hash', models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ('gasprice', models.BigIntegerField(blank=True, null=True)),
                ('gas', models.BigIntegerField(blank=True, null=True)),
                ('level', models.PositiveIntegerField(blank=True, db_index=True, null=True)),
                ('last_fail', models.DateTimeField(auto_now_add=True, null=True)),
                ('state', models.CharField(choices=[('held', 'Held'), ('aborted', 'Aborted'), ('deploy', 'To deploy'), ('deploying', 'Deploying'), ('retrying', 'Retrying'), ('confirm', 'To confirm'), ('confirming', 'Confirming'), ('done', 'Finished')], db_index=True, default='held', max_length=200)),
                ('error', models.TextField(blank=True)),
                ('history', models.JSONField(default=list)),
                ('blockchain', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='djwebdapp.blockchain')),
                ('sender', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='transaction_sent', to='djwebdapp.address')),
            ],
        ),
        migrations.CreateModel(
            name='SmartContract',
            fields=[
                ('transaction_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='djwebdapp.transaction')),
                ('address', models.CharField(blank=True, max_length=255, null=True)),
                ('storage', models.JSONField(blank=True, default=dict)),
            ],
            bases=('djwebdapp.transaction',),
        ),
        migrations.CreateModel(
            name='Node',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Node name, generated from endpoint if empty', max_length=100)),
                ('endpoint', models.CharField(max_length=255)),
                ('is_active', models.BooleanField(default=True, help_text='Check to activate this node')),
                ('priority', models.IntegerField(default=0, help_text='Nodes with the highest priority will be used first')),
                ('blockchain', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='djwebdapp.blockchain')),
            ],
        ),
        migrations.CreateModel(
            name='Explorer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Explorer name, generated from url template if empty', max_length=100)),
                ('url_template', models.CharField(blank=True, max_length=255, null=True)),
                ('is_active', models.BooleanField(default=True, help_text='Check to activate this explorer')),
                ('blockchain', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='djwebdapp.blockchain')),
            ],
        ),
        migrations.AddField(
            model_name='address',
            name='blockchain',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='djwebdapp.blockchain'),
        ),
        migrations.AddField(
            model_name='address',
            name='owner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='Transfer',
            fields=[
                ('transaction_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='djwebdapp.transaction')),
                ('amount', models.PositiveIntegerField(blank=True, db_index=True, null=True)),
                ('receiver', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='transfer_received', to='djwebdapp.address')),
            ],
            bases=('djwebdapp.transaction',),
        ),
        migrations.CreateModel(
            name='Call',
            fields=[
                ('transaction_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='djwebdapp.transaction')),
                ('function', models.CharField(blank=True, db_index=True, max_length=100, null=True)),
                ('args', models.JSONField(blank=True, default=list, null=True)),
                ('storage', models.JSONField(blank=True, default=dict, null=True)),
                ('contract', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='call_set', to='djwebdapp.smartcontract')),
            ],
            bases=('djwebdapp.transaction',),
        ),
    ]