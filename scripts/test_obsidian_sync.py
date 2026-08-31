#!/usr/bin/env python3
"""Focused regression tests for nested generated/the-real learning notes."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))

import obsidian_sync as sync


FRONTMATTER = """---
type: vibelearn
layer: {layer}
created: 2026-08-30
horizon: short+long
field:
  - type-systems/traits
tags:
  - compare-generated-lived-knowledge
---

# {title}

Evidence-backed body.
"""


class NestedLearningLayerTests(unittest.TestCase):
    def setUp(self):
        self.previous_vault = sync.VAULT
        self.temp = tempfile.TemporaryDirectory()
        sync.VAULT = self.temp.name
        self.concept_dir = os.path.join(
            self.temp.name,
            "System III  Rust",
            "Concepts",
            "Trait",
        )
        os.makedirs(self.concept_dir)
        self.generated = os.path.join(self.concept_dir, "11 trait 语法.md")
        self.real = os.path.join(self.concept_dir, "Traits_v1.md")
        self._write(self.generated, FRONTMATTER.format(layer="generated", title="11 · trait 语法"))
        self._write(
            self.real,
            FRONTMATTER.format(
                layer="the real",
                title="Traits_v1：一次真实学习之后的 Trait 地形",
            ),
        )

    def tearDown(self):
        sync.VAULT = self.previous_vault
        self.temp.cleanup()

    @staticmethod
    def _write(path, content):
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)

    def test_real_note_inherits_rung_and_public_parent_path(self):
        ladder = sync.ladder_of(self.real)
        self.assertIsNotNone(ladder)
        self.assertEqual(ladder["order"], 11)
        self.assertEqual(ladder["concept"], "Trait")
        self.assertEqual(sync.post_slug(self.real), "11-trait-syntax/traits-v1")

    def test_generated_note_keeps_stable_parent_url(self):
        ladder = sync.ladder_of(self.generated)
        self.assertIsNotNone(ladder)
        self.assertEqual(sync.post_slug(self.generated), "11-trait-syntax")

    def test_public_frontmatter_exposes_only_archive_projection(self):
        post = sync.to_post(self.real, draft=False)
        self.assertIn("concept: \"Trait\"", post)
        self.assertIn("layer: 'the real'", post)
        self.assertIn("revision: 1", post)
        self.assertIn("draft: false", post)
        self.assertNotIn("field:", post)
        self.assertNotIn("tags:", post)


if __name__ == "__main__":
    unittest.main()
