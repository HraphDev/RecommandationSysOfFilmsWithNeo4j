# film_app/migrations/0001_initial.py
from django.db import migrations, models
import uuid
import django.utils.timezone

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        # If your project has no dependencies for auth or other apps, leave empty
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('username', models.CharField(max_length=150, unique=True)),
                ('email', models.EmailField(unique=True, max_length=254)),
                ('first_name', models.CharField(max_length=30, blank=True)),
                ('last_name', models.CharField(max_length=30, blank=True)),
                ('profile_picture', models.CharField(max_length=255, default='default.jpg')),
                ('is_admin', models.BooleanField(default=False)),
                ('is_superuser', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now)),
                ('last_login', models.DateTimeField(null=True, blank=True)),
                ('favorite_movies', models.JSONField(default=list)),
                ('watchlist', models.JSONField(default=list)),
                ('watched_movies', models.JSONField(default=list)),
                ('neo4j_id', models.CharField(max_length=100, blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
