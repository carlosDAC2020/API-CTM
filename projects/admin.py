from django.contrib import admin
from . import models

admin.site.register(models.Project)

admin.site.register(models.Research)

admin.site.register(models.ItemContext)

admin.site.register(models.Opportunity)

admin.site.register(models.Report)

admin.site.register(models.Note)