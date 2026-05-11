from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_report'),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='nova_analysis',
            field=models.TextField(blank=True, help_text='AI-generated analysis by NOVA'),
        ),
        migrations.AddField(
            model_name='report',
            name='admin_notes',
            field=models.TextField(blank=True, help_text='Admin notes added during review'),
        ),
        migrations.AlterField(
            model_name='report',
            name='status',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('draft', 'Draft'),
                    ('submitted', 'Submitted'),
                    ('approved', 'Approved'),
                    ('rejected', 'Rejected'),
                ],
                default='draft',
            ),
        ),
    ]