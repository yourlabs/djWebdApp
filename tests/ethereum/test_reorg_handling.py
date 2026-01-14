"""
Tests for blockchain reorganization handling in EthereumEventProvider.

These tests verify:
1. Reorg detection via block hash comparison
2. Event deletion on reorg (with CASCADE to domain objects)
3. Transaction state reset on reorg
4. IndexedBlock cleanup on reorg
5. Confirmation-based normalization delay
6. Re-indexing after reorg fetches correct canonical data

Test Setup Requirements:
- Local Ethereum node (anvil/hardhat) that supports block manipulation
- Ability to simulate reorgs (mine competing chains)

Note: Some tests may require mocking if the local node doesn't support
true reorg simulation. In that case, we mock the block hash changes.
"""
import pytest
from unittest.mock import MagicMock

from djwebdapp.models import Blockchain, IndexedBlock
from djwebdapp_ethereum.models import (
    EthereumTransaction,
    EthereumEvent,
)
from djwebdapp_ethereum.provider import EthereumEventProvider
from djwebdapp_example_ethereum.models import (
    FA12EthereumBalanceMovement,
    FA12EthereumBalance,
)


@pytest.fixture
def blockchain():
    """Create a test blockchain with EthereumEventProvider."""
    return Blockchain.objects.create(
        name='test_eth',
        provider_class='djwebdapp_ethereum.provider.EthereumEventProvider',
        is_active=True,
        unit='eth',
        unit_micro='wei',
        min_confirmations=2,
        index_level=100,
    )


@pytest.fixture
def indexed_blocks(blockchain):
    """Create IndexedBlock records for testing reorg detection."""
    blocks = []
    for level in range(95, 101):
        block = IndexedBlock.objects.create(
            blockchain=blockchain,
            level=level,
            block_hash=f'0x{"a" * 64}',  # Same hash pattern for all
        )
        blocks.append(block)
    return blocks


@pytest.fixture
def mock_provider(blockchain):
    """Create a provider with mocked client."""
    provider = EthereumEventProvider(blockchain=blockchain)
    provider._client = MagicMock()
    return provider


class TestFindForkPoint:
    """Tests for find_fork_point() method - finding the last common ancestor."""

    def test_no_reorg_when_most_recent_hash_matches(self, mock_provider, indexed_blocks):
        """No reorg detected when the most recent indexed block hash matches."""
        # Mock client to return same hashes as stored
        mock_provider.client.eth.get_block_number = MagicMock(return_value=100)

        def get_block(level):
            return {'hash': MagicMock(to_0x_hex=lambda: f'0x{"a" * 64}')}

        mock_provider.client.eth.get_block = get_block

        result = mock_provider.find_fork_point()
        assert result is None

    def test_finds_fork_point_when_hash_differs(self, mock_provider, indexed_blocks):
        """Fork point found when block hashes diverge."""
        # Indexed blocks: 95-100 all with hash 'aaa...'
        # Current chain: 95-97 match, 98-100 have different hash
        # Fork point should be 97, so reorg_level = 98
        mock_provider.client.eth.get_block_number = MagicMock(return_value=100)

        def get_block(level):
            if level >= 98:
                return {'hash': MagicMock(to_0x_hex=lambda: f'0x{"b" * 64}')}
            return {'hash': MagicMock(to_0x_hex=lambda: f'0x{"a" * 64}')}

        mock_provider.client.eth.get_block = get_block

        result = mock_provider.find_fork_point()
        assert result == 98  # First divergent block

    def test_finds_fork_point_when_chain_shrinks(self, mock_provider, indexed_blocks):
        """Fork point found when chain is shorter than indexed level."""
        # Indexed up to 100, but chain shrunk to 95
        # Need to find where the fork actually happened
        mock_provider.client.eth.get_block_number = MagicMock(return_value=95)

        def get_block(level):
            if level > 95:
                raise Exception("Block not found")
            if level >= 93:
                # Blocks 93-95 have different hashes (part of reorg)
                return {'hash': MagicMock(to_0x_hex=lambda: f'0x{"b" * 64}')}
            return {'hash': MagicMock(to_0x_hex=lambda: f'0x{"a" * 64}')}

        mock_provider.client.eth.get_block = get_block

        # Fork point is at 92 (last matching block), so reorg_level = 93
        # But we only have indexed blocks starting at 95, so it returns 95
        result = mock_provider.find_fork_point()
        assert result == 95  # Earliest indexed block in our test fixture

    def test_finds_deep_fork_point(self, mock_provider, blockchain):
        """Fork point found even for deep reorgs."""
        blockchain.index_level = 100
        blockchain.save()

        # Create indexed blocks from 90 to 100
        for level in range(90, 101):
            IndexedBlock.objects.create(
                blockchain=blockchain,
                level=level,
                block_hash=f'0x{"a" * 64}',
            )

        mock_provider.client.eth.get_block_number = MagicMock(return_value=100)

        def get_block(level):
            # Fork at block 92 - blocks 93+ have different hashes
            if level >= 93:
                return {'hash': MagicMock(to_0x_hex=lambda: f'0x{"b" * 64}')}
            return {'hash': MagicMock(to_0x_hex=lambda: f'0x{"a" * 64}')}

        mock_provider.client.eth.get_block = get_block

        result = mock_provider.find_fork_point()
        assert result == 93  # First divergent block (after fork point 92)

    def test_no_reorg_when_no_indexed_blocks(self, mock_provider, blockchain):
        """No reorg when there are no indexed blocks to check."""
        # No indexed blocks exist for this blockchain
        mock_provider.client.eth.get_block_number = MagicMock(return_value=100)
        result = mock_provider.find_fork_point()
        assert result is None

    def test_no_reorg_when_index_level_is_none(self, blockchain):
        """No reorg when blockchain.index_level is None."""
        blockchain.index_level = None
        blockchain.save()

        provider = EthereumEventProvider(blockchain=blockchain)
        provider._client = MagicMock()

        result = provider.find_fork_point()
        assert result is None


class TestReorgHandling:
    """Tests for reorg() method - the actual cleanup."""

    def test_reorg_deletes_events_at_and_after_reorg_level(
        self, mock_provider, blockchain, indexed_blocks
    ):
        """Events at or after reorg level are deleted."""
        # Create a contract and events at various levels
        contract = EthereumTransaction.objects.create(
            blockchain=blockchain,
            kind='contract',
            address='0x' + 'c' * 40,
            state='done',
            level=90,
        )

        tx_before = EthereumTransaction.objects.create(
            blockchain=blockchain,
            hash='0x' + '1' * 64,
            level=95,
            state='done',
        )
        tx_at_reorg = EthereumTransaction.objects.create(
            blockchain=blockchain,
            hash='0x' + '2' * 64,
            level=98,
            state='done',
        )
        tx_after_reorg = EthereumTransaction.objects.create(
            blockchain=blockchain,
            hash='0x' + '3' * 64,
            level=100,
            state='done',
        )

        # Create events
        event_before = EthereumEvent.objects.create(
            name='Transfer',
            contract=contract,
            transaction=tx_before,
            event_index=0,
        )
        event_at_reorg = EthereumEvent.objects.create(
            name='Transfer',
            contract=contract,
            transaction=tx_at_reorg,
            event_index=0,
        )
        event_after_reorg = EthereumEvent.objects.create(
            name='Transfer',
            contract=contract,
            transaction=tx_after_reorg,
            event_index=0,
        )

        # Mock reorg detection at level 98
        def get_block(level):
            if level >= 98:
                return {'hash': MagicMock(to_0x_hex=lambda: f'0x{"b" * 64}')}
            return {'hash': MagicMock(to_0x_hex=lambda: f'0x{"a" * 64}')}

        mock_provider.client.eth.get_block = get_block
        mock_provider.client.eth.get_block_number = MagicMock(return_value=100)

        # Execute reorg
        result = mock_provider.reorg()

        assert result is True

        # Event before reorg should still exist
        assert EthereumEvent.objects.filter(pk=event_before.pk).exists()

        # Events at and after reorg should be deleted
        assert not EthereumEvent.objects.filter(pk=event_at_reorg.pk).exists()
        assert not EthereumEvent.objects.filter(pk=event_after_reorg.pk).exists()

    def test_reorg_resets_transactions_at_and_after_reorg_level(
        self, mock_provider, blockchain, indexed_blocks
    ):
        """Transactions at or after reorg level are reset to deleted state."""
        tx_before = EthereumTransaction.objects.create(
            blockchain=blockchain,
            hash='0x' + '1' * 64,
            level=95,
            state='done',
            normalized=True,
        )
        tx_at_reorg = EthereumTransaction.objects.create(
            blockchain=blockchain,
            hash='0x' + '2' * 64,
            level=98,
            state='done',
            address='0x' + 'a' * 40,
            normalized=True,
        )

        # Mock reorg at level 98
        def get_block(level):
            if level >= 98:
                return {'hash': MagicMock(to_0x_hex=lambda: f'0x{"b" * 64}')}
            return {'hash': MagicMock(to_0x_hex=lambda: f'0x{"a" * 64}')}

        mock_provider.client.eth.get_block = get_block
        mock_provider.client.eth.get_block_number = MagicMock(return_value=100)

        mock_provider.reorg()

        # Refresh from DB
        tx_before.refresh_from_db()
        tx_at_reorg.refresh_from_db()

        # Transaction before reorg should be unchanged
        assert tx_before.state == 'done'
        assert tx_before.level == 95
        assert tx_before.normalized is True

        # Transaction at reorg should be reset
        assert tx_at_reorg.state == 'deleted'
        assert tx_at_reorg.level is None
        assert tx_at_reorg.hash is None
        assert tx_at_reorg.address is None
        assert tx_at_reorg.normalized is False

    def test_reorg_deletes_indexed_blocks_at_and_after_reorg_level(
        self, mock_provider, blockchain, indexed_blocks
    ):
        """IndexedBlock records at or after reorg level are deleted."""
        # Mock reorg at level 98
        def get_block(level):
            if level >= 98:
                return {'hash': MagicMock(to_0x_hex=lambda: f'0x{"b" * 64}')}
            return {'hash': MagicMock(to_0x_hex=lambda: f'0x{"a" * 64}')}

        mock_provider.client.eth.get_block = get_block
        mock_provider.client.eth.get_block_number = MagicMock(return_value=100)

        mock_provider.reorg()

        # Blocks before reorg should exist
        assert IndexedBlock.objects.filter(
            blockchain=blockchain, level__lt=98
        ).count() == 3  # levels 95, 96, 97

        # Blocks at and after reorg should be deleted
        assert IndexedBlock.objects.filter(
            blockchain=blockchain, level__gte=98
        ).count() == 0

    def test_reorg_resets_blockchain_index_level(
        self, mock_provider, blockchain, indexed_blocks
    ):
        """Blockchain index_level is reset to just before reorg."""
        # Mock reorg at level 98
        def get_block(level):
            if level >= 98:
                return {'hash': MagicMock(to_0x_hex=lambda: f'0x{"b" * 64}')}
            return {'hash': MagicMock(to_0x_hex=lambda: f'0x{"a" * 64}')}

        mock_provider.client.eth.get_block = get_block
        mock_provider.client.eth.get_block_number = MagicMock(return_value=100)

        mock_provider.reorg()

        blockchain.refresh_from_db()
        assert blockchain.index_level == 97  # One before reorg level

    def test_reorg_handles_chain_shrink(self, mock_provider, blockchain, indexed_blocks):
        """Reorg detected when chain head is less than index_level."""
        # Chain shrunk from 100 to 95
        mock_provider.client.eth.get_block_number = MagicMock(return_value=95)

        result = mock_provider.reorg()

        assert result is True
        blockchain.refresh_from_db()
        assert blockchain.index_level == 94


class TestConfirmationBasedNormalization:
    """Tests for confirmation-based normalization delay."""

    def test_unconfirmed_events_not_normalized(self, mock_provider, blockchain):
        """Events within confirmation window are not returned for normalization."""
        contract = EthereumTransaction.objects.create(
            blockchain=blockchain,
            kind='contract',
            address='0x' + 'c' * 40,
            state='done',
            level=90,
        )

        # Current head is 100, min_confirmations is 2
        # So only events at level <= 98 should be normalized
        mock_provider.client.eth.get_block_number = MagicMock(return_value=100)

        # Transaction at level 99 (unconfirmed)
        tx_unconfirmed = EthereumTransaction.objects.create(
            blockchain=blockchain,
            hash='0x' + '1' * 64,
            level=99,
            state='done',
        )
        EthereumEvent.objects.create(
            name='Transfer',
            contract=contract,
            transaction=tx_unconfirmed,
            event_index=0,
            normalized=False,
        )

        # Transaction at level 98 (confirmed)
        tx_confirmed = EthereumTransaction.objects.create(
            blockchain=blockchain,
            hash='0x' + '2' * 64,
            level=98,
            state='done',
        )
        EthereumEvent.objects.create(
            name='Transfer',
            contract=contract,
            transaction=tx_confirmed,
            event_index=0,
            normalized=False,
        )

        to_normalize = mock_provider.get_transactions_to_normalize()

        # Only the confirmed transaction should be returned
        assert tx_confirmed in to_normalize
        assert tx_unconfirmed not in to_normalize

    def test_confirmed_events_normalized(self, mock_provider, blockchain):
        """Events past confirmation window are returned for normalization."""
        contract = EthereumTransaction.objects.create(
            blockchain=blockchain,
            kind='contract',
            address='0x' + 'c' * 40,
            state='done',
            level=90,
        )

        mock_provider.client.eth.get_block_number = MagicMock(return_value=100)

        # Transaction at level 95 (well confirmed)
        tx = EthereumTransaction.objects.create(
            blockchain=blockchain,
            hash='0x' + '1' * 64,
            level=95,
            state='done',
        )
        EthereumEvent.objects.create(
            name='Transfer',
            contract=contract,
            transaction=tx,
            event_index=0,
            normalized=False,
        )

        to_normalize = mock_provider.get_transactions_to_normalize()

        assert tx in to_normalize


class TestStoreBlockHash:
    """Tests for store_block_hash() method."""

    def test_stores_new_block_hash(self, mock_provider, blockchain):
        """New block hash is stored correctly."""
        mock_provider.client.eth.get_block = MagicMock(
            return_value={'hash': MagicMock(to_0x_hex=lambda: f'0x{"d" * 64}')}
        )

        mock_provider.store_block_hash(150)

        indexed_block = IndexedBlock.objects.get(blockchain=blockchain, level=150)
        assert indexed_block.block_hash == f'0x{"d" * 64}'

    def test_updates_existing_block_hash(self, mock_provider, blockchain):
        """Existing block hash is updated on re-index."""
        # Create existing record
        IndexedBlock.objects.create(
            blockchain=blockchain,
            level=150,
            block_hash=f'0x{"a" * 64}',
        )

        # Re-index with different hash
        mock_provider.client.eth.get_block = MagicMock(
            return_value={'hash': MagicMock(to_0x_hex=lambda: f'0x{"b" * 64}')}
        )

        mock_provider.store_block_hash(150)

        indexed_block = IndexedBlock.objects.get(blockchain=blockchain, level=150)
        assert indexed_block.block_hash == f'0x{"b" * 64}'


class TestCascadeDelete:
    """
    Tests for CASCADE delete behavior.

    These tests verify that domain objects with FK to EthereumEvent
    are properly deleted when events are deleted during reorg.

    Uses FA12EthereumBalanceMovement which FKs to EthereumEvent with CASCADE.
    """

    def test_cascade_delete_removes_balance_movements(self, blockchain):
        """
        When events are deleted, FA12EthereumBalanceMovement records
        are cascade deleted and balances are recalculated.

        This test directly creates the domain objects to isolate the
        cascade delete behavior from the full normalization flow.
        """
        from djwebdapp.models import Account
        from djwebdapp_example_ethereum.models import FA12Ethereum

        # Create contract
        fa12_contract = FA12Ethereum.objects.create(
            blockchain=blockchain,
            token_name='Test Token',
            token_symbol='TT',
            kind='contract',
            address='0x' + 'c' * 40,
            state='done',
            level=100,
        )

        # Create account (set balance to avoid signal trying to fetch from chain)
        admin, _ = Account.objects.get_or_create(
            blockchain=blockchain,
            address='0x' + 'a' * 40,
            defaults={'balance': 1000},
        )

        # Create transactions at different levels
        tx1 = EthereumTransaction.objects.create(
            blockchain=blockchain,
            hash='0x' + '1' * 64,
            level=101,
            state='done',
        )
        tx2 = EthereumTransaction.objects.create(
            blockchain=blockchain,
            hash='0x' + '2' * 64,
            level=102,
            state='done',
        )

        # Create events
        event1 = EthereumEvent.objects.create(
            name='Mint',
            contract=fa12_contract,
            transaction=tx1,
            event_index=0,
        )
        event2 = EthereumEvent.objects.create(
            name='Mint',
            contract=fa12_contract,
            transaction=tx2,
            event_index=0,
        )

        # Create balance movements (simulating normalized data)
        FA12EthereumBalanceMovement.objects.create(
            event=event1,
            fa12=fa12_contract,
            account=admin,
            amount=100,
        )
        FA12EthereumBalanceMovement.objects.create(
            event=event2,
            fa12=fa12_contract,
            account=admin,
            amount=200,
        )

        # Verify initial state
        assert FA12EthereumBalanceMovement.objects.filter(fa12=fa12_contract).count() == 2
        balance = FA12EthereumBalance.objects.get(fa12=fa12_contract, account=admin)
        assert balance.balance == 300

        # Simulate reorg: delete event at level 102
        EthereumEvent.objects.filter(
            contract=fa12_contract,
            transaction__level__gte=102,
        ).delete()

        # Verify cascade delete - the movement linked to deleted event is gone
        assert FA12EthereumBalanceMovement.objects.filter(fa12=fa12_contract).count() == 1

        # Note: This test simulates direct event deletion (e.g., manual cleanup).
        # In real reorg flow, the reorg_Mint hook is called BEFORE deletion,
        # which explicitly deletes movements and recalculates balances.
        # See test_reorg_mint_hook_recalculates_balance for the full flow.

    def test_reorg_cascade_deletes_domain_objects(
        self, mock_provider, blockchain, indexed_blocks
    ):
        """
        Full reorg flow: reorg() deletes events which cascade deletes
        FA12EthereumBalanceMovement records.
        """
        from djwebdapp.models import Account
        from djwebdapp_example_ethereum.models import FA12Ethereum

        # Create contract
        fa12_contract = FA12Ethereum.objects.create(
            blockchain=blockchain,
            token_name='Test Token',
            token_symbol='TT',
            kind='contract',
            address='0x' + 'c' * 40,
            state='done',
            level=90,
        )

        # Create account (set balance to avoid signal trying to fetch from chain)
        admin, _ = Account.objects.get_or_create(
            blockchain=blockchain,
            address='0x' + 'a' * 40,
            defaults={'balance': 1000},
        )

        # Create transactions at different levels
        tx_before = EthereumTransaction.objects.create(
            blockchain=blockchain,
            hash='0x' + '1' * 64,
            level=95,
            state='done',
        )
        tx_at_reorg = EthereumTransaction.objects.create(
            blockchain=blockchain,
            hash='0x' + '2' * 64,
            level=98,
            state='done',
        )

        # Create events
        event_before = EthereumEvent.objects.create(
            name='Mint',
            contract=fa12_contract,
            transaction=tx_before,
            event_index=0,
        )
        event_at_reorg = EthereumEvent.objects.create(
            name='Mint',
            contract=fa12_contract,
            transaction=tx_at_reorg,
            event_index=0,
        )

        # Create balance movements
        FA12EthereumBalanceMovement.objects.create(
            event=event_before,
            fa12=fa12_contract,
            account=admin,
            amount=100,
        )
        FA12EthereumBalanceMovement.objects.create(
            event=event_at_reorg,
            fa12=fa12_contract,
            account=admin,
            amount=200,
        )

        # Verify initial state
        assert FA12EthereumBalanceMovement.objects.filter(fa12=fa12_contract).count() == 2
        balance = FA12EthereumBalance.objects.get(fa12=fa12_contract, account=admin)
        assert balance.balance == 300

        # Mock reorg at level 98
        def get_block(level):
            if level >= 98:
                return {'hash': MagicMock(to_0x_hex=lambda: f'0x{"b" * 64}')}
            return {'hash': MagicMock(to_0x_hex=lambda: f'0x{"a" * 64}')}

        mock_provider.client.eth.get_block = get_block
        mock_provider.client.eth.get_block_number = MagicMock(return_value=100)

        # Execute reorg
        result = mock_provider.reorg()
        assert result is True

        # Verify event at reorg level was deleted
        assert not EthereumEvent.objects.filter(pk=event_at_reorg.pk).exists()
        assert EthereumEvent.objects.filter(pk=event_before.pk).exists()

        # Verify the reorg_Mint hook deleted the balance movement
        assert FA12EthereumBalanceMovement.objects.filter(fa12=fa12_contract).count() == 1

        # Verify balance was recalculated by reorg_Mint hook
        balance.refresh_from_db()
        assert balance.balance == 100  # Only the first mint remains

    def test_reorg_hook_called_before_delete(
        self, mock_provider, blockchain, indexed_blocks
    ):
        """
        Normalizer's reorg_{EventName} hook is called before events are deleted.
        """
        from djwebdapp.models import Account
        from djwebdapp.normalizers import Normalizer
        from djwebdapp_example_ethereum.models import FA12Ethereum
        from unittest.mock import patch, MagicMock

        # Create contract with normalizer
        fa12_contract = FA12Ethereum.objects.create(
            blockchain=blockchain,
            token_name='Test Token',
            token_symbol='TT',
            kind='contract',
            address='0x' + 'c' * 40,
            state='done',
            level=90,
        )

        # Create account
        admin, _ = Account.objects.get_or_create(
            blockchain=blockchain,
            address='0x' + 'a' * 40,
            defaults={'balance': 1000},
        )

        # Create transaction and event at reorg level
        tx = EthereumTransaction.objects.create(
            blockchain=blockchain,
            hash='0x' + '1' * 64,
            level=98,
            state='done',
        )
        event = EthereumEvent.objects.create(
            name='Mint',
            contract=fa12_contract,
            transaction=tx,
            event_index=0,
        )

        # Track reorg_event calls
        reorg_calls = []
        original_reorg_event = Normalizer.reorg_event

        @classmethod
        def tracking_reorg_event(cls, event, contract):
            reorg_calls.append((event.name, contract))
            return original_reorg_event(event, contract)

        # Mock reorg at level 98
        def get_block(level):
            if level >= 98:
                return {'hash': MagicMock(to_0x_hex=lambda: f'0x{"b" * 64}')}
            return {'hash': MagicMock(to_0x_hex=lambda: f'0x{"a" * 64}')}

        mock_provider.client.eth.get_block = get_block
        mock_provider.client.eth.get_block_number = MagicMock(return_value=100)

        # Patch the base Normalizer class
        with patch.object(Normalizer, 'reorg_event', tracking_reorg_event):
            mock_provider.reorg()

        # Verify reorg_event was called for the Mint event
        assert len(reorg_calls) == 1
        assert reorg_calls[0][0] == 'Mint'

    def test_reorg_mint_hook_recalculates_balance(
        self, mock_provider, blockchain, indexed_blocks
    ):
        """
        FA12EthereumNormalizer.reorg_Mint deletes movement and recalculates balance.
        """
        from djwebdapp.models import Account
        from djwebdapp_example_ethereum.models import FA12Ethereum

        # Create contract with normalizer
        fa12_contract = FA12Ethereum.objects.create(
            blockchain=blockchain,
            token_name='Test Token',
            token_symbol='TT',
            kind='contract',
            address='0x' + 'c' * 40,
            state='done',
            level=90,
        )

        # Create account
        admin, _ = Account.objects.get_or_create(
            blockchain=blockchain,
            address='0x' + 'a' * 40,
            defaults={'balance': 1000},
        )

        # Create transactions at different levels
        tx_before = EthereumTransaction.objects.create(
            blockchain=blockchain,
            hash='0x' + '1' * 64,
            level=95,
            state='done',
        )
        tx_at_reorg = EthereumTransaction.objects.create(
            blockchain=blockchain,
            hash='0x' + '2' * 64,
            level=98,
            state='done',
        )

        # Create events
        event_before = EthereumEvent.objects.create(
            name='Mint',
            contract=fa12_contract,
            transaction=tx_before,
            event_index=0,
        )
        event_at_reorg = EthereumEvent.objects.create(
            name='Mint',
            contract=fa12_contract,
            transaction=tx_at_reorg,
            event_index=0,
        )

        # Create balance movements (simulating normalized state)
        FA12EthereumBalanceMovement.objects.create(
            event=event_before,
            fa12=fa12_contract,
            account=admin,
            amount=100,
        )
        FA12EthereumBalanceMovement.objects.create(
            event=event_at_reorg,
            fa12=fa12_contract,
            account=admin,
            amount=200,
        )

        # Verify initial balance
        balance = FA12EthereumBalance.objects.get(fa12=fa12_contract, account=admin)
        assert balance.balance == 300

        # Mock reorg at level 98
        def get_block(level):
            if level >= 98:
                return {'hash': MagicMock(to_0x_hex=lambda: f'0x{"b" * 64}')}
            return {'hash': MagicMock(to_0x_hex=lambda: f'0x{"a" * 64}')}

        mock_provider.client.eth.get_block = get_block
        mock_provider.client.eth.get_block_number = MagicMock(return_value=100)

        # Execute reorg - this should call reorg_Mint which recalculates balance
        mock_provider.reorg()

        # Verify balance was recalculated by the reorg_Mint hook
        balance.refresh_from_db()
        assert balance.balance == 100  # Only the first mint (100) remains


class TestIndexWithReorg:
    """Integration tests for index() with reorg handling."""

    def test_index_returns_early_on_reorg(self, mock_provider, blockchain, indexed_blocks):
        """index() returns immediately after handling reorg."""
        # Mock reorg at level 98
        def get_block(level):
            if level >= 98:
                return {'hash': MagicMock(to_0x_hex=lambda: f'0x{"b" * 64}')}
            return {'hash': MagicMock(to_0x_hex=lambda: f'0x{"a" * 64}')}

        mock_provider.client.eth.get_block = get_block
        mock_provider.client.eth.get_block_number = MagicMock(return_value=100)

        # index() should return after reorg handling
        mock_provider.index()

        # Verify reorg was handled
        blockchain.refresh_from_db()
        assert blockchain.index_level == 97

    def test_index_continues_normally_without_reorg(self, mock_provider, blockchain):
        """index() proceeds normally when no reorg detected."""
        blockchain.index_level = None
        blockchain.save()

        # Mock normal operation - no reorg
        mock_provider.client.eth.get_block_number = MagicMock(return_value=5)
        mock_provider.client.eth.get_logs = MagicMock(return_value=[])
        mock_provider.client.eth.get_block = MagicMock(
            return_value={'hash': MagicMock(to_0x_hex=lambda: f'0x{"a" * 64}')}
        )

        mock_provider.index()

        blockchain.refresh_from_db()
        assert blockchain.index_level == 5


# Pytest configuration for running these tests
pytestmark = pytest.mark.django_db(transaction=True)
