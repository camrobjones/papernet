# Generated by Django 2.1.7 on 2020-04-15 00:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('papernet', '0003_auto_20200414_2336'),
    ]

    operations = [
        migrations.AddField(
            model_name='reference',
            name='cit_key',
            field=models.CharField(blank=True, max_length=128),
        ),
    ]
