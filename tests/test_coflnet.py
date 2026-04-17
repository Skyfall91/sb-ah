import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sources.coflnet import CoflnetClient, NoDataError


@pytest.fixture
def client():
    return CoflnetClient()


@pytest.mark.asyncio
async def test_get_price_history_returns_data(client):
    mock_data = [
        {"time": "2025-01-01T00:00:00", "avg": 80_000.0, "min": 75_000.0, "max": 85_000.0, "volume": 1200},
        {"time": "2025-01-02T00:00:00", "avg": 82_000.0, "min": 78_000.0, "max": 86_000.0, "volume": 1100},
    ]
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=MagicMock(
            json=AsyncMock(return_value=mock_data),
            status=200
        ))
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_get.return_value = mock_ctx
        result = await client.get_price_history("GRIFFIN_FEATHER", days=90)
    assert len(result) == 2
    assert result[0]["avg"] == 80_000.0


@pytest.mark.asyncio
async def test_empty_response_raises_no_data(client):
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=MagicMock(
            json=AsyncMock(return_value=[]),
            status=200
        ))
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_get.return_value = mock_ctx
        with pytest.raises(NoDataError):
            await client.get_price_history("UNKNOWN_ITEM", days=90)


@pytest.mark.asyncio
async def test_timeout_raises_original_exception(client):
    import aiohttp
    with patch("aiohttp.ClientSession.get", side_effect=aiohttp.ServerTimeoutError):
        with pytest.raises(aiohttp.ServerTimeoutError):
            await client.get_price_history("ANY_ITEM", days=90)


@pytest.mark.asyncio
async def test_get_median_price(client):
    mock_data = [
        {"time": "2025-01-01T00:00:00", "avg": 80_000.0, "min": 75_000.0, "max": 85_000.0, "volume": 1200},
    ]
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=MagicMock(
            json=AsyncMock(return_value=mock_data),
            status=200
        ))
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_get.return_value = mock_ctx
        median = await client.get_median_price("ENCHANTED_DIAMOND")
    assert median == 80_000.0
