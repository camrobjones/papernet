# Generated by Django 3.1.1 on 2020-09-16 02:54

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('papernet', '0017_tag_created'),
    ]

    operations = [
        migrations.RenameField(
            model_name='journal',
            old_name='issn_online',
            new_name='electronic_issn',
        ),
        migrations.AddField(
            model_name='journal',
            name='last_retrieved',
            field=models.DateTimeField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name='journal',
            name='last_updated',
            field=models.DateTimeField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name='journal',
            name='print_issn',
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name='journal',
            name='publisher',
            field=models.CharField(blank=True, default='', max_length=128),
        ),
        migrations.AddField(
            model_name='journal',
            name='total_doi',
            field=models.IntegerField(default=0),
        ),
        migrations.CreateModel(
            name='Topic',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128)),
                ('code', models.IntegerField(unique=True)),
                ('topic_type', models.CharField(blank=True, default='', max_length=128)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('journal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='topics', related_query_name='topic', to='papernet.journal')),
            ],
            options={
                'unique_together': {('code', 'journal', 'topic_type')},
            },
        ),
    ]
