# Create a normalized FA12 model for this Tezos contract
from djwebdapp_example.models import FA12
fa12 = FA12.objects.create(tezos_contract=contract)

# reverse relation works as usual
assert contract.fa12

# but we did noting to normalize the mint calls so far
assert contract.fa12.mint_set.count() == 0

# Trigger Mint objects creation for each call that has *already* been indexed
for call in fa12.tezos_contract.call_set.all():
    call.save()  # trigger post_save signal

# mint calls were normalized
assert contract.fa12.mint_set.count() == 1

# balance was calculated
from djwebdapp_example.models import Balance
assert Balance.objects.first().balance == 1000
