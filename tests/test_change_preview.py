from copy import deepcopy
import unittest

from docs_radar.change_preview import highlighted_change


class ChangePreviewTests(unittest.TestCase):
    def setUp(self):
        self.facts = [dict(id="closure", value="2027-01-20", version=1, audience="providers"),
                      dict(id="other", value="Unchanged", version=1)]
        self.change = dict(evidence_type="synthetic", fact_id="closure",
                           old_value="2027-01-20", new_value="2099-01-01",
                           old_version=1, new_version=2)

    def test_inline_changes_keep_context_literals_and_other_facts(self):
        text = "# Deadline\nCloses {{fact:closure}}. Literal 2027-01-20. {{fact:other}}"
        before = deepcopy((self.facts, self.change))
        result = highlighted_change(text, self.facts, self.change)
        self.assertIn('# Deadline\nCloses <del', result)
        self.assertIn('2027-01-20</del>', result)
        self.assertIn('2099-01-01</ins>. Literal 2027-01-20. Unchanged', result)
        self.assertEqual((self.facts, self.change), before)

    def test_each_reference_is_highlighted(self):
        result = highlighted_change('{{fact:closure}} / {{fact:closure}}', self.facts, self.change)
        self.assertEqual(result.count('<del '), 2)
        self.assertEqual(result.count('<ins '), 2)

    def test_unrelated_document_has_no_preview(self):
        self.assertIsNone(highlighted_change('Literal 2027-01-20; {{fact:other}}', self.facts, self.change))

    def test_untrusted_markup_is_escaped(self):
        self.change['new_value'] = '<img src=x onerror="alert(1)">'
        self.facts[1]['value'] = '<script>bad()</script>'
        result = highlighted_change('<script>bad()</script> {{fact:closure}} {{fact:other}}', self.facts, self.change)
        self.assertNotIn('<script>', result)
        self.assertNotIn('<img', result)
        self.assertIn('&lt;img', result)
        self.assertEqual(result.count('&lt;script&gt;'), 2)

    def test_stale_or_non_synthetic_changes_are_rejected(self):
        for field, value in [('old_value', 'wrong'), ('old_version', 9), ('evidence_type', 'public')]:
            with self.subTest(field=field):
                change = {**self.change, field: value}
                with self.assertRaises(ValueError):
                    highlighted_change('{{fact:closure}}', self.facts, change)

    def test_unknown_references_are_rejected(self):
        with self.assertRaises(ValueError):
            highlighted_change('{{fact:missing}} {{fact:closure}}', self.facts, self.change)
