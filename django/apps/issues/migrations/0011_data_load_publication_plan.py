from pathlib import Path
from django.db import migrations
from utils.migration_helpers import unload_fixture, load_fixture

fixture = Path(__file__).parent / 'pub-plan-2010-2015.json'


class Migration(migrations.Migration):

    dependencies = [
        ('issues', '0010_auto_20160924_2128'),
    ]

    operations = [
        migrations.RunPython(
            code=load_fixture(str(fixture)),
            reverse_code=unload_fixture('issues', ['Issue', 'PrintIssue']),
        ),
    ]
