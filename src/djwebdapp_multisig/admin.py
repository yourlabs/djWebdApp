from django.contrib import admin

from djwebdapp_multisig import models

admin.site.register(models.MultisigContract)
admin.site.register(models.AddAuthorizedContractCall)
