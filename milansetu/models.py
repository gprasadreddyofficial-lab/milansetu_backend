from django.db import models

# Create your models here.

class ProfileDetails(models.Model):
    id = models.BigAutoField(primary_key=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    age = models.IntegerField(blank=True, null=True)
    height_cm = models.IntegerField(blank=True, null=True)
    religion = models.CharField(max_length=100, blank=True, null=True)
    mother_tongue = models.CharField(max_length=100, blank=True, null=True)
    marital_status = models.CharField(max_length=100, blank=True, null=True)
    father_occupation = models.CharField(max_length=255, blank=True, null=True)
    mother_occupation = models.CharField(max_length=255, blank=True, null=True)
    siblings_count = models.IntegerField(blank=True, null=True)
    siblings_details = models.TextField(blank=True, null=True)
    family_values = models.CharField(max_length=255, blank=True, null=True)
    industry = models.CharField(max_length=255, blank=True, null=True)
    education = models.CharField(max_length=255, blank=True, null=True)
    current_designation = models.CharField(max_length=255, blank=True, null=True)
    current_company = models.CharField(max_length=255, blank=True, null=True)
    annual_income_min = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    annual_income_max = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    income_unit = models.CharField(max_length=20, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    time_of_birth = models.TimeField(blank=True, null=True)
    birth_place = models.CharField(max_length=255, blank=True, null=True)
    zodiac_sign = models.CharField(max_length=100, blank=True, null=True)
    manglik_status = models.CharField(max_length=50, blank=True, null=True)
    kundali_url = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'profile_details'