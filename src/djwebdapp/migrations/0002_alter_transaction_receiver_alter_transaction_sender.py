# Generated by Django 4.0.2 on 2022-02-20 12:15

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('djwebdapp', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='receiver',
            field=models.ForeignKey(blank=True, help_text='Receiver address, if this is a transfer', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(model_name)s_received', to='djwebdapp.account'),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='sender',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(model_name)s_sent', to='djwebdapp.account'),
        ),
    ]