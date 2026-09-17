from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='ksldc',
            old_name='created_at',
            new_name='time',
        ),
        migrations.AlterField(
            model_name='ksldc',
            name='time',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
