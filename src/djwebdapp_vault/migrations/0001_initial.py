# Generated by Django 3.1.14 on 2021-12-24 10:01

from django.db import migrations, models
import django.db.models.deletion
import fernet_fields.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('djwebdapp', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Wallet',
            fields=[
                ('address_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='djwebdapp.address')),
                ('mnemonic', fernet_fields.fields.EncryptedTextField()),
                ('revealed', models.BooleanField(default=False)),
            ],
            bases=('djwebdapp.address',),
        ),
    ]
