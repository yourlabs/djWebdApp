# Generated by Django 4.0.2 on 2022-02-09 21:37

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
