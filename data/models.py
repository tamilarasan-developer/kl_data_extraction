from django.db import models


class ksldc(models.Model):

    escom_name = models.CharField(
        max_length=100
    )

    bio_mass = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    cogen = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    mini_hydro = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    wind = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    solar = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    total = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    # Exact format:
    # 2026-09-10 14:30:00
    date_time = models.CharField(
        max_length=19,
        null=True,
        blank=True
    )

    # Exact format:
    # 2026-09-10 14:34:42
    updated_time = models.CharField(
        max_length=19,
        null=True,
        blank=True
    )

    class Meta:
        db_table = "ksldc_data"

    def __str__(self):
        return self.escom_name