# Generated by Django 4.0.2 on 2022-03-30 08:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djwebdapp', '0002_alter_transaction_receiver_alter_transaction_sender'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='txgroup',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='hash',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterUniqueTogether(
            name='transaction',
            unique_together={('hash', 'txgroup')},
        ),
    ]
