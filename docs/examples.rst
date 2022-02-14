djWebdApp Examples
~~~~~~~~~~~~~~~~~~

Chaining blockchain calls
-------------------------

This example demonstrates how to generate an initial mint call to deploy
whenever a new contract is deployed:

.. code-block:: python

    from djwebdapp_tezos.models import TezosTransaction
    from django.db.models import signals
    from django.dispatch import receiver


    @receiver(signals.post_save, sender=TezosTransaction)
    def auto_mint(sender, instance, **kwargs):
        if not instance.address:
            # we're not a contract or not ready
            return

        if instance.call_set.count() > 1:
            # we have a mint already
            return

        mint = TezosTransaction.objects.create(
            sender=instance.sender,
            state='deploy',
            max_fails=2,
            contract=instance,
            function='mint',
            args=(
                instance.sender.address,
                1000,
            ),
        )
