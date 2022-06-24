# Generated by Django 2.1.7 on 2020-09-03 13:36

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('papernet', '0009_auto_20200903_1309'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='last_active',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='reader',
            name='last_active',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]