# Generated by Django 3.1.14 on 2022-02-16 12:08

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('djwebdapp', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='transaction',
            name='contract_address',
        ),
        migrations.RemoveField(
            model_name='transaction',
            name='datetime',
        ),
    ]