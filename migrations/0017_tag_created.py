# Generated by Django 2.1.7 on 2020-09-05 12:29

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('papernet', '0016_auto_20200905_1136'),
    ]

    operations = [
        migrations.AddField(
            model_name='tag',
            name='created',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]