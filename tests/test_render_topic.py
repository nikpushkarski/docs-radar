import json
from pathlib import Path
import unittest

from render_topic import render_topic


ROOT = Path(__file__).resolve().parents[1]


class TopicRenderingTest(unittest.TestCase):
    def setUp(self):
        self.facts = json.loads(
            (ROOT / "data/facts.json").read_text(encoding="utf-8")
        )
        self.topics = {
            name: (ROOT / "content" / name).read_text(encoding="utf-8")
            for name in (
                "provider-migration-checklist.md", "rupa-view-only.md"
            )
        }

    def test_both_topics_render_stored_date(self):
        for name, topic in self.topics.items():
            with self.subTest(topic=name):
                self.assertIn("{{fact:rupa-login-closure-date}}", topic)
                self.assertNotIn("2027-01-20", topic)
                rendered = render_topic(topic, self.facts)
                self.assertIn("login access closes on 2027-01-20.", rendered)
                self.assertNotIn("{{fact:", rendered)

    def test_unknown_fact_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown fact ID: missing"):
            render_topic("Closes on {{fact:missing}}.", self.facts)

    def test_one_changed_fact_updates_both_rendered_topics(self):
        # Synthetic change in memory only; this is not a Fullscript date.
        changed_facts = [fact.copy() for fact in self.facts]
        for fact in changed_facts:
            if fact["id"] == "rupa-login-closure-date":
                fact["value"] = "2099-01-01"
                fact["version"] += 1
        for name, topic in self.topics.items():
            with self.subTest(topic=name):
                rendered = render_topic(topic, changed_facts)
                self.assertIn("login access closes on 2099-01-01.", rendered)
                self.assertNotIn("2027-01-20", rendered)
                self.assertNotIn("{{fact:", rendered)
                self.assertEqual(
                    (ROOT / "content" / name).read_text(encoding="utf-8"),
                    topic,
                )
        self.assertEqual(
            json.loads((ROOT / "data/facts.json").read_text(encoding="utf-8")),
            self.facts,
        )


if __name__ == "__main__":
    unittest.main()
