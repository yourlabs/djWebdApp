"""
Example models to demonstrate features of djwebdapp.
"""


from django.db import models


class FA12(models.Model):
    """
    Model representing an FA12 contract on at least one blockchain.

    .. py:attribute:: name

        The name of the FA12 token, ie.: "Your New Token"

    .. py:attribute:: symbol

        Symbol of the FA12 token, ie.: "YNT"

    .. note:: You wouldn't need to have relations to contracts on every
              blockchain, but we have them here so that we are later able to
              demonstrate inter-blockchain mirroring.
    """
    tezos_contract = models.OneToOneField(
        'djwebdapp_tezos.TezosTransaction',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    ethereum_contract = models.OneToOneField(
        'djwebdapp_ethereum.EthereumTransaction',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    name = models.CharField(
        max_length=200,
        null=True,
        blank=True,
    )
    symbol = models.CharField(
        max_length=10,
        null=True,
        blank=True,
    )


class Mint(models.Model):
    """
    Model representing a mint() call on an FA12 contract.

    .. py:attribute:: address

        Recipient address for the mint.

    .. py:attribute:: value

        Amount of tokens minted.

    .. note:: You wouldn't need to have relations to contract calls on every
              blockchain, but we have them here so that we are later able to
              demonstrate inter-blockchain mirroring.
    """
    fa12 = models.ForeignKey(
        'FA12',
        on_delete=models.CASCADE,
    )
    tezos_call = models.OneToOneField(
        'djwebdapp_tezos.TezosTransaction',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    ethereum_call = models.OneToOneField(
        'djwebdapp_ethereum.EthereumTransaction',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    address = models.ForeignKey(
        'djwebdapp.Account',
        on_delete=models.CASCADE,
    )
    value = models.PositiveIntegerField()

    def __str__(self):
        return f'mint({self.address.address}, {self.value})'


class Balance(models.Model):
    """
    Model representing the balance of an address on an FA12 token.
    """
    fa12 = models.ForeignKey(
        'FA12',
        on_delete=models.CASCADE,
    )
    address = models.ForeignKey(
        'djwebdapp.Account',
        on_delete=models.CASCADE,
        related_name='fa12_balance_set',
    )
    balance = models.PositiveIntegerField()

    class Meta:
        unique_together = (
            ('fa12', 'address'),
        )

    def __str__(self):
        return f'{self.address} balance: {self.balance}'


# importing other documentation code snippets concerning signals here
from .ethereum.mint_normalize import mint_normalize_ethereum  # noqa
from .tezos.mint_normalize import mint_normalize_tezos        # noqa
