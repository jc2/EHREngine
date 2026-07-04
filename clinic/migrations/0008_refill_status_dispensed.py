from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clinic", "0007_refill_auth_controlled_only"),
    ]

    operations = [
        migrations.AlterField(
            model_name="refillrequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("APPROVED", "Approved"),
                    ("NEEDS_PROVIDER_REVIEW", "Needs provider review"),
                    ("DENIED", "Denied"),
                    ("DISPENSED", "Dispensed"),
                ],
                db_index=True,
                max_length=30,
            ),
        ),
    ]
