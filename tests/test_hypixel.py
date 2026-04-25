import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sources.hypixel import HypixelClient


@pytest.fixture
def client():
    return HypixelClient(api_key="test-key")


@pytest.mark.asyncio
async def test_get_bazaar_returns_products(client):
    mock_response = {
        "success": True,
        "products": {
            "ENCHANTED_DIAMOND": {
                "product_id": "ENCHANTED_DIAMOND",
                "sell_summary": [{"pricePerUnit": 20_500_000, "amount": 10}],
                "buy_summary": [{"pricePerUnit": 18_200_000, "amount": 10}],
                "quick_status": {"buyVolume": 1000, "sellVolume": 1000,
                                 "buyMovingWeek": 500_000, "sellMovingWeek": 500_000}
            }
        }
    }
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=MagicMock(
            json=AsyncMock(return_value=mock_response),
            status=200
        ))
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_get.return_value = mock_ctx
        result = await client.get_bazaar()
    assert "ENCHANTED_DIAMOND" in result
    assert result["ENCHANTED_DIAMOND"]["sell_summary"][0]["pricePerUnit"] == 20_500_000


@pytest.mark.asyncio
async def test_get_bazaar_timeout_raises(client):
    import aiohttp
    with patch("aiohttp.ClientSession.get", side_effect=aiohttp.ServerTimeoutError):
        with pytest.raises(aiohttp.ServerTimeoutError):
            await client.get_bazaar()


