from django.db import models


# Create your models here.

class GenericSystemSettings(models.Model):
    prop_type_choices = (
        ('Email', 'Email'),
        ('Other', 'Other')
    )

    prop_key = models.CharField(max_length=100)
    prop_value = models.CharField(max_length=500)
    prop_type = models.CharField(max_length=10, choices=prop_type_choices)
    description = models.CharField(max_length=100, null=True, blank=True)
    remark = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = 'generic_system_settings'
