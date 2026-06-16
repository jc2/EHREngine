from django.db import models

from .insurance import InsuranceType


class BillingRule(models.Model):
    """Deterministic visit-cost lookup (Epic 3: Financial determinism).

    Cost is a pure function of (insurance_type, specialty) resolved by a tiered
    cascade, so the LLM only identifies the specialty while Django computes the
    auditable, reproducible dollar amount:

      Tier 1 — exact match:     insurance_type AND specialty both set.
      Tier 2 — specialty default: insurance_type NULL, specialty set.
      Tier 3 — global fallback:   insurance_type NULL AND specialty NULL.

    Nullable columns are what encode the tiers: a more specific (non-null) rule
    wins over a broader (null) one. `estimate_visit_cost` returns the fixed_cost
    of the FIRST tier that matches.
    """

    insurance_type = models.CharField(
        max_length=3,
        choices=InsuranceType.choices,
        null=True,
        blank=True,
        help_text="Insurance plan type this rule applies to. Leave blank for an insurance-agnostic rule.",
    )
    specialty = models.ForeignKey(
        "clinic.MedicalDepartment",
        on_delete=models.CASCADE,
        related_name="billing_rules",
        null=True,
        blank=True,
        help_text="Specialty this rule applies to. Leave blank for the global fallback rule.",
    )
    fixed_cost = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["insurance_type", "specialty"],
                name="unique_billing_rule_scope",
            )
        ]
        ordering = ["specialty__name", "insurance_type"]

    def __str__(self):
        ins = self.insurance_type or "ANY"
        spec = self.specialty.name if self.specialty else "ANY"
        return f"BillingRule({ins} / {spec}) = ${self.fixed_cost}"
