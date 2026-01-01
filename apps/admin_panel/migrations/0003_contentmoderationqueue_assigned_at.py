# Generated manually for assigned_at field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_panel', '0002_messagetemplate_systemmessage_pushnotification_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='contentmoderationqueue',
            name='assigned_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]