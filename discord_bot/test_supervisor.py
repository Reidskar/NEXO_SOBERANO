import unittest
from unittest.mock import AsyncMock, MagicMock
import discord
from supervisor import Supervisor

class TestSupervisor(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot = MagicMock()
        self.cog = Supervisor(self.bot)

    async def test_nsfw_detection(self):
        self.assertTrue(self.cog._is_nsfw_content("Esto es porno"))
        self.assertFalse(self.cog._is_nsfw_content("Mensaje normal"))

    async def test_spam_detection(self):
        user_id = 123
        now = 1000.0
        dq = self.cog.user_messages[user_id]
        for i in range(10):
            dq.append(now + i)
        # Simula ventana de spam
        while dq and dq[0] < now + 10 - self.cog.SPAM_WINDOW_SECONDS:
            dq.popleft()
        self.assertGreaterEqual(len(dq), self.cog.SPAM_THRESHOLD)

    async def test_duplicate_link_detection(self):
        user_id = 456
        link = "http://spam.com"
        for _ in range(4):
            self.cog.user_links[user_id][link] += 1
        self.assertGreaterEqual(self.cog.user_links[user_id][link], self.cog.DUP_LINK_THRESHOLD)

if __name__ == "__main__":
    unittest.main()
