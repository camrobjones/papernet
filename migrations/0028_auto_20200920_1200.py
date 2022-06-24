# Generated by Django 3.1.1 on 2020-09-20 12:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('papernet', '0027_auto_20200920_1120'),
    ]

    operations = [
        migrations.AddField(
            model_name='papertext',
            name='link',
            field=models.URLField(blank=True, default=None, null=True),
        ),
        migrations.AlterField(
            model_name='papertext',
            name='updated',
            field=models.DateTimeField(blank=True, default=None, null=True),
        ),
    ]