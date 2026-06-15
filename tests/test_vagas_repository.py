from unittest.mock import MagicMock, patch

import pytest

from database.vagas_repository import get_vaga_by_external_id


@pytest.fixture
def mock_supabase_chain():
    """Build a mock chain: client.table().select().filter().limit().execute()."""
    mock_execute = MagicMock()
    mock_limit = MagicMock()
    mock_limit.execute.return_value = mock_execute
    mock_filter = MagicMock()
    mock_filter.limit.return_value = mock_limit
    mock_select = MagicMock()
    mock_select.filter.return_value = mock_filter
    mock_table = MagicMock()
    mock_table.select.return_value = mock_select
    mock_client = MagicMock()
    mock_client.table.return_value = mock_table
    return mock_client, mock_execute, mock_filter


def test_get_vaga_by_external_id_returns_vaga_when_found(mock_supabase_chain):
    mock_client, mock_execute, mock_filter = mock_supabase_chain
    expected = {
        "id": 1,
        "external_id": "gupy-123",
        "titulo": "Desenvolvedor Python",
        "empresa": "Empresa Teste",
    }
    mock_execute.data = [expected]

    with patch("database.vagas_repository.db") as mock_db:
        mock_db.client = mock_client
        result = get_vaga_by_external_id("gupy-123")

    assert result == expected
    mock_client.table.assert_called_once_with("vagas")
    mock_filter.limit.assert_called_once_with(1)
    mock_select = mock_client.table.return_value.select.return_value
    mock_select.filter.assert_called_once_with("external_id", "eq", "gupy-123")


def test_get_vaga_by_external_id_returns_none_when_not_found(mock_supabase_chain):
    mock_client, mock_execute, _ = mock_supabase_chain
    mock_execute.data = []

    with patch("database.vagas_repository.db") as mock_db:
        mock_db.client = mock_client
        result = get_vaga_by_external_id("inexistente")

    assert result is None


def test_get_vaga_by_external_id_raises_when_client_not_initialized():
    with patch("database.vagas_repository.db") as mock_db:
        mock_db.client = None
        with pytest.raises(RuntimeError, match="Supabase client is not initialized"):
            get_vaga_by_external_id("any-id")
