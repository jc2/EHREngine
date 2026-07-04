from django.db import migrations


def authorize_non_controlled_refills(apps, schema_editor):
    RefillRequest = apps.get_model("clinic", "RefillRequest")
    pending_non_controlled = RefillRequest.objects.filter(
        authorization_status="PENDING",
    ).exclude(status="DENIED").filter(
        prescription__medication__is_controlled_substance=False,
    )
    for refill in pending_non_controlled.iterator():
        refill.authorization_status = "AUTHORIZED"
        if not refill.processed_at:
            refill.processed_at = refill.requested_at
        refill.save(update_fields=["authorization_status", "processed_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("clinic", "0006_refill_authorization_status"),
    ]

    operations = [
        migrations.RunPython(
            authorize_non_controlled_refills,
            migrations.RunPython.noop,
        ),
    ]
