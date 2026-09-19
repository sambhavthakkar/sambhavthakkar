import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import update_stats


class UpdateStatsTest(unittest.TestCase):
    def test_unchanged_cards_do_not_create_another_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            readme = root / "README.md"
            readme.write_text('<img src="stats-strip.svg">\n<!--STATS_UPDATED-->\n')
            with (
                patch.object(update_stats, "ROOT", root),
                patch.object(update_stats, "README_PATH", readme),
                patch.object(update_stats, "CACHE_PATH", root / ".stats-cache.json"),
                patch.object(update_stats, "fetch_with_retry", return_value="<svg/>"),
                patch.object(update_stats, "save_cache", wraps=update_stats.save_cache) as save,
            ):
                update_stats.main()
                self.assertEqual(save.call_count, 1)
                update_stats.main()
                self.assertEqual(save.call_count, 1)


if __name__ == "__main__":
    unittest.main()
