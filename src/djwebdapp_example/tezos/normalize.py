# Create a normalized FA12 model for this Tezos contract
from djwebdapp_example.models import FA12
fa12 = FA12.objects.create(tezos_contract=contract)

# reverse relation works as usual
assert contract.fa12

# mint calls were normalized
assert contract.fa12.mint_set.count() == 1

# balance was calculated
from djwebdapp_example.models import Balance
assert Balance.objects.first().balance == 1000
