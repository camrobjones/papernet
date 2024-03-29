# Generated by Django 3.1.1 on 2020-09-21 05:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('papernet', '0001_squashed_0028_auto_20200920_1200'),
    ]

    operations = [
        migrations.AlterField(
            model_name='affiliation',
            name='created',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='author',
            name='created',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='institution',
            name='created',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='journal',
            name='created',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='paper',
            name='created',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='project',
            name='created',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='publication',
            name='created',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='reference',
            name='citing_doi',
            field=models.CharField(max_length=128),
        ),
        migrations.AlterField(
            model_name='reference',
            name='created',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='tag',
            name='created',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
