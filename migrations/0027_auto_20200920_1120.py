# Generated by Django 3.1.1 on 2020-09-20 11:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('papernet', '0026_papertext'),
    ]

    operations = [
        migrations.AlterField(
            model_name='papertext',
            name='publication',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='papernet.publication'),
        ),
    ]
