# Django Shell Command - Simple Version
# Copy and paste this into: python manage.py shell

from manufacturing.models import PackagingMaterial
from django.db import transaction

# Show what will be updated
print("Checking PackagingMaterial records...")
records_to_update = PackagingMaterial.objects.filter(
    qty_filled_can_reject__isnull=False
).exclude(qty_filled_can_reject=0)

print(f"Found {records_to_update.count()} records to update")

# Preview first few records
for pm in records_to_update[:3]:
    original_product_reject = pm.qty_product_reject or 0
    can_reject_value = pm.qty_filled_can_reject
    new_value = original_product_reject + can_reject_value
    print(f"ID {pm.id}: {original_product_reject} + {can_reject_value} = {new_value}")

# Perform the update
with transaction.atomic():
    updated = 0
    for pm in records_to_update:
        original_product_reject = pm.qty_product_reject or 0
        can_reject_value = pm.qty_filled_can_reject
        pm.qty_product_reject = original_product_reject + can_reject_value
        pm.save()
        updated += 1
        print(f"Updated ID {pm.id}: {original_product_reject} + {can_reject_value} = {pm.qty_product_reject}")
    
    print(f"Successfully updated {updated} records!")

print("Migration completed - qty_filled_can_reject values have been ADDED to qty_product_reject")
