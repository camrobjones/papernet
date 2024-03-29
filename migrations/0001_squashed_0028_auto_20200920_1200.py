# Generated by Django 3.1.1 on 2020-09-21 05:55

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    replaces = [('papernet', '0001_initial'), ('papernet', '0002_auto_20200414_2016'), ('papernet', '0003_auto_20200414_2336'), ('papernet', '0004_reference_cit_key'), ('papernet', '0005_auto_20200415_0033'), ('papernet', '0006_auto_20200530_0310'), ('papernet', '0007_paper_updated'), ('papernet', '0008_auto_20200903_1217'), ('papernet', '0009_auto_20200903_1309'), ('papernet', '0010_auto_20200903_1336'), ('papernet', '0011_auto_20200903_1342'), ('papernet', '0012_auto_20200903_1655'), ('papernet', '0013_requestlog'), ('papernet', '0014_auto_20200904_2205'), ('papernet', '0015_auto_20200905_0905'), ('papernet', '0016_auto_20200905_1136'), ('papernet', '0017_tag_created'), ('papernet', '0018_auto_20200916_0254'), ('papernet', '0019_auto_20200916_0302'), ('papernet', '0020_auto_20200916_0512'), ('papernet', '0021_auto_20200916_0730'), ('papernet', '0022_auto_20200916_0841'), ('papernet', '0023_auto_20200916_1746'), ('papernet', '0024_auto_20200916_1750'), ('papernet', '0025_auto_20200916_2220'), ('papernet', '0026_papertext'), ('papernet', '0027_auto_20200920_1120'), ('papernet', '0028_auto_20200920_1200')]

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Author',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=128)),
                ('last_name', models.CharField(max_length=128)),
                ('created', models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now)),
                ('scholar', models.URLField(blank=True)),
                ('twitter', models.URLField(blank=True)),
                ('website', models.URLField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Institution',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128)),
                ('url', models.URLField(blank=True)),
                ('city', models.CharField(blank=True, max_length=128)),
                ('post_code', models.CharField(blank=True, max_length=128)),
                ('street', models.CharField(blank=True, max_length=128)),
                ('country', models.CharField(blank=True, max_length=128)),
                ('created', models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now)),
                ('raw', models.TextField(blank=True, default='')),
            ],
        ),
        migrations.CreateModel(
            name='Journal',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(blank=True, max_length=128)),
                ('abbreviation', models.CharField(blank=True, max_length=30)),
                ('issn', models.CharField(max_length=128, unique=True)),
                ('electronic_issn', models.CharField(blank=True, max_length=128)),
                ('journal_type', models.CharField(blank=True, max_length=128)),
                ('created', models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now)),
                ('last_retrieved', models.DateTimeField(blank=True, default=None, null=True)),
                ('last_updated', models.DateTimeField(blank=True, default=None, null=True)),
                ('print_issn', models.CharField(blank=True, max_length=128)),
                ('publisher', models.CharField(blank=True, default='', max_length=128)),
                ('total_doi', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Paper',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('short_title', models.CharField(blank=True, max_length=50)),
                ('doi', models.CharField(max_length=128, unique=True)),
                ('abstract', models.TextField(blank=True, default='')),
                ('article_type', models.CharField(blank=True, max_length=128)),
                ('retrieved', models.DateTimeField(blank=True, default=None, null=True)),
                ('updated', models.DateTimeField(blank=True, default=None, null=True)),
                ('keywords', models.TextField(blank=True, default='')),
                ('created', models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now)),
                ('is_referenced_by_count', models.IntegerField(default=0)),
                ('references_count', models.IntegerField(default=0)),
                ('subtitle', models.CharField(blank=True, default='', max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name='Authorship',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.CharField(blank=True, max_length=128)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='papernet.author')),
                ('paper', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='papernet.paper')),
            ],
        ),
        migrations.CreateModel(
            name='Reader',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('last_active', models.DateTimeField(default=django.utils.timezone.now)),
                ('image', models.ImageField(default='papernet/guest.jpg', upload_to='papernet/')),
                ('bio', models.TextField(blank=True, default='')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Affiliation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.CharField(blank=True, max_length=128)),
                ('authorship', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='papernet.authorship')),
                ('institution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='papernet.institution')),
                ('created', models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now)),
            ],
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=80)),
                ('description', models.TextField(blank=True, default='')),
                ('primary', models.BooleanField(default=False)),
                ('reader', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='papernet.reader')),
                ('last_active', models.DateTimeField(default=django.utils.timezone.now)),
                ('created', models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now)),
            ],
        ),
        migrations.CreateModel(
            name='RequestLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField()),
                ('ua_header', models.CharField(max_length=200)),
                ('params', models.TextField()),
                ('start_time', models.DateTimeField(blank=True, default=None, null=True)),
                ('end_time', models.DateTimeField(blank=True, default=None, null=True)),
                ('delta', models.FloatField(default=0)),
                ('response_code', models.IntegerField(default=0)),
                ('wait', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Perusal',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('notes', models.TextField(blank=True, default='')),
                ('status', models.CharField(blank=True, default='None', max_length=150)),
                ('status_updated', models.DateTimeField(default=django.utils.timezone.now)),
                ('rating', models.IntegerField(default=0)),
                ('priority', models.IntegerField(default=0)),
                ('paper', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='papernet.paper')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='papernet.project')),
                ('reader', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='papernet.reader')),
                ('last_active', models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.CharField(max_length=50)),
                ('perusal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='papernet.perusal')),
                ('created', models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now)),
            ],
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
        migrations.CreateModel(
            name='Container',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='Publication',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('published', models.DateField(blank=True, null=True)),
                ('published_online', models.DateField(blank=True, null=True)),
                ('file', models.FileField(blank=True, default=None, null=True, upload_to='papernet/publications/')),
                ('volume', models.CharField(blank=True, max_length=128)),
                ('issue', models.CharField(blank=True, max_length=128)),
                ('pages', models.CharField(blank=True, max_length=128)),
                ('source', models.URLField(blank=True, null=True)),
                ('journal', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='papernet.journal')),
                ('paper', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='papernet.paper')),
                ('created', models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now)),
                ('published_print', models.DateField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Reference',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('author', models.CharField(blank=True, max_length=128)),
                ('journal', models.CharField(blank=True, max_length=128)),
                ('title', models.CharField(blank=True, max_length=128)),
                ('publication_year', models.CharField(blank=True, max_length=128)),
                ('cited_paper', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='cited_by', to='papernet.paper')),
                ('citing_paper', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='citations', to='papernet.paper')),
                ('cited_doi', models.CharField(max_length=128)),
                ('cit_key', models.CharField(blank=True, max_length=128)),
                ('created', models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now)),
                ('citing_doi', models.CharField(default='', max_length=128)),
                ('oci', models.CharField(blank=True, default='', max_length=128)),
            ],
            options={
                'unique_together': {('citing_doi', 'cited_doi')},
            },
        ),
        migrations.CreateModel(
            name='PaperText',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pdf', models.FileField(blank=True, default=None, null=True, upload_to='papernet/files/papers/')),
                ('header', models.TextField(blank=True, default='')),
                ('abstract', models.TextField(blank=True, default='')),
                ('keywords', models.TextField(blank=True, default='')),
                ('body', models.TextField(blank=True, default='')),
                ('acknowledgements', models.TextField(blank=True, default='')),
                ('references', models.TextField(blank=True, default='')),
                ('notes', models.TextField(blank=True, default='')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(blank=True, default=None, null=True)),
                ('paper', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='papernet.paper')),
                ('publication', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='papernet.publication')),
                ('link', models.URLField(blank=True, default=None, null=True)),
            ],
        ),
    ]
