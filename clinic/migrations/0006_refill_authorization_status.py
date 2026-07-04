from django.db import migrations, models


def backfill_authorization_status(apps, schema_editor):
    RefillRequest = apps.get_model("clinic", "RefillRequest")
    for refill in RefillRequest.objects.all().iterator():
        if refill.status == "APPROVED":
            refill.authorization_status = "AUTHORIZED"
        else:
            refill.authorization_status = "PENDING"
        refill.save(update_fields=["authorization_status"])


class Migration(migrations.Migration):

    dependencies = [
        ("clinic", "0005_human_escalation"),
    ]

    operations = [
        migrations.AddField(
            model_name="refillrequest",
            name="authorization_status",
            field=models.CharField(
                choices=[
                    ("PENDING", "Pending authorization"),
                    ("AUTHORIZED", "Authorized"),
                ],
                db_index=True,
                default="PENDING",
                max_length=12,
            ),
        ),
        migrations.RunPython(
            backfill_authorization_status,
            migrations.RunPython.noop,
        ),
    ]
