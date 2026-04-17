import pytest
from unittest.mock import patch
from models import Opportunity
from notify import Notifier


@pytest.fixture
def notifier():
    return Notifier(min_profit_notify=500_000)


def test_high_profit_triggers_notification(notifier):
    opp = Opportunity("BAZAAR", "ENCHANTED_DIAMOND", "Enchanted Diamond",
                      2_300_000, "JETZT KAUFEN", {}, "high")
    with patch("subprocess.run") as mock_run:
        notifier.notify_if_threshold(opp)
        assert mock_run.called


def test_low_profit_no_notification(notifier):
    opp = Opportunity("BAZAAR", "CHEAP_ITEM", "Cheap Item",
                      200_000, "JETZT KAUFEN", {}, "low")
    with patch("subprocess.run") as mock_run:
        notifier.notify_if_threshold(opp)
        assert not mock_run.called


def test_notification_contains_item_name(notifier):
    opp = Opportunity("NPC", "SAND", "Sand",
                      600_000, "JETZT KAUFEN", {}, "high")
    with patch("subprocess.run") as mock_run:
        notifier.notify_if_threshold(opp)
        args = mock_run.call_args_list[0][0][0]
        script = " ".join(args)
        assert "Sand" in script
