# Generated by Django 5.2.1 on 2025-06-04 07:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0004_alter_result_options_result_updated_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
