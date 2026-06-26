import unittest
from unittest.mock import patch

from src.notification import NotificationSender


class FakeConfig:
    def __init__(self, notification_config):
        self.notification_config = notification_config


class NotificationSenderTests(unittest.TestCase):
    def test_batch_notification_does_not_send_when_wechat_disabled(self) -> None:
        with patch(
            "src.notification.get_config",
            return_value=FakeConfig({"enable_wechat": False}),
        ):
            sender = NotificationSender()

        with patch.object(sender, "send_wechat") as mock_send_wechat:
            count = sender.send_batch_notification(
                [{"title": "High paper", "relevance": "High"}]
            )

        self.assertEqual(count, 0)
        mock_send_wechat.assert_not_called()


if __name__ == "__main__":
    unittest.main()
