"""Tests for Sway configurable document access rules (document_access)."""
from __future__ import annotations
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

class TestDocumentAccess(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.base = Path(self.t.name)
        self.docs = self.base / 'docs'
        self.docs.mkdir(parents=True)
        
        # Populate various test documents
        (self.docs / 'overview.md').write_text('# Overview\nPublic overview.')
        (self.docs / 'notes.txt').write_text('General notes.')
        (self.docs / 'root.json').write_text('{"public": true}')
        
        (self.docs / 'strategy').mkdir()
        (self.docs / 'strategy' / 'q1.md').write_text('# Q1 Strategy')
        (self.docs / 'strategy' / 'confidential.md').write_text('# Confidential Strategy')
        
        (self.docs / 'strategy' / '2026').mkdir()
        (self.docs / 'strategy' / '2026' / 'annual.md').write_text('# 2026 Annual Plan')
        
        (self.docs / 'reports').mkdir()
        (self.docs / 'reports' / 'doc1.txt').write_text('Report 1')
        (self.docs / 'reports' / 'doc12.txt').write_text('Report 12')
        (self.docs / 'reports' / 'docA.txt').write_text('Report A')
        
        (self.docs / 'internal').mkdir()
        (self.docs / 'internal' / 'secret.md').write_text('Top Secret')
        (self.docs / 'internal' / 'budget.csv').write_text('item,cost\nserver,100')

    def make_config(self, doc_access: dict | None = None) -> dict[str, str]:
        cfg: dict = {
            'version': 1,
            'organizations': {
                'testorg': {
                    'documents_path': str(self.docs),
                    'brands': {'main': {}},
                }
            }
        }
        if doc_access is not None:
            cfg['organizations']['testorg']['document_access'] = doc_access
            
        cfg_file = self.base / 'config.yaml'
        cfg_file.write_text(yaml.safe_dump(cfg))
        return dict(os.environ, SWAY_CONFIG=str(cfg_file))

    def cli(self, env: dict[str, str], *args, success=True) -> tuple[int, dict]:
        r = subprocess.run([sys.executable, '-m', *args], cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
        if success and r.returncode != 0:
            self.fail(f'Command failed {args}:\nSTDERR: {r.stderr}\nSTDOUT: {r.stdout}')
        try:
            out = json.loads(r.stdout)
        except json.JSONDecodeError:
            self.fail(f'Non-JSON output from {args}:\nSTDOUT: {r.stdout}\nSTDERR: {r.stderr}')
        return r.returncode, out

    def test_backward_compatibility_no_document_access(self):
        """When document_access is omitted, all files under documents_path are accessible."""
        env = self.make_config(None)
        
        # list_docs should show all files
        _, out = self.cli(env, 'tools.documents.list_docs', '--org', 'testorg')
        self.assertTrue(out['ok'])
        doc_ids = {d['id'] for d in out['documents']}
        self.assertIn('overview.md', doc_ids)
        self.assertIn('strategy/q1.md', doc_ids)
        self.assertIn('internal/secret.md', doc_ids)
        
        # read_docs should allow reading any valid file
        _, out = self.cli(env, 'tools.documents.read_docs', '--org', 'testorg', 'internal/secret.md')
        self.assertTrue(out['ok'])
        self.assertIn('Top Secret', out['documents'][0]['content'])

    def test_allow_list_exact_and_wildcard(self):
        """When allow is provided, only matching files are accessible."""
        env = self.make_config({
            'allow': [
                'overview.md',
                'strategy/*',
            ]
        })
        
        # list_docs should only return overview.md and direct children of strategy/
        _, out = self.cli(env, 'tools.documents.list_docs', '--org', 'testorg')
        doc_ids = {d['id'] for d in out['documents']}
        self.assertEqual(doc_ids, {'overview.md', 'strategy/q1.md', 'strategy/confidential.md'})
        
        # overview.md and strategy/q1.md should be readable
        _, out = self.cli(env, 'tools.documents.read_docs', '--org', 'testorg', 'overview.md', 'strategy/q1.md')
        self.assertTrue(out['ok'])
        self.assertEqual(len(out['documents']), 2)
        
        # notes.txt is not in allow, so direct read must fail
        code, out = self.cli(env, 'tools.documents.read_docs', '--org', 'testorg', 'notes.txt', success=False)
        self.assertNotEqual(code, 0)
        self.assertFalse(out['ok'])
        self.assertIn('denied by policy', out['error'])

    def test_single_star_does_not_cross_directories(self):
        """Wildcard * matches only within a single directory segment."""
        env = self.make_config({
            'allow': ['strategy/*']
        })
        
        _, out = self.cli(env, 'tools.documents.list_docs', '--org', 'testorg')
        doc_ids = {d['id'] for d in out['documents']}
        self.assertIn('strategy/q1.md', doc_ids)
        # strategy/2026/annual.md should NOT match strategy/*
        self.assertNotIn('strategy/2026/annual.md', doc_ids)
        
        # Direct read on nested file should fail
        code, out = self.cli(env, 'tools.documents.read_docs', '--org', 'testorg', 'strategy/2026/annual.md', success=False)
        self.assertNotEqual(code, 0)
        self.assertFalse(out['ok'])

    def test_question_mark_wildcard(self):
        """Wildcard ? matches exactly one non-separator character."""
        env = self.make_config({
            'allow': ['reports/doc?.txt']
        })
        
        _, out = self.cli(env, 'tools.documents.list_docs', '--org', 'testorg')
        doc_ids = {d['id'] for d in out['documents']}
        self.assertEqual(doc_ids, {'reports/doc1.txt', 'reports/docA.txt'})
        self.assertNotIn('reports/doc12.txt', doc_ids)
        
        # doc12.txt direct read should fail
        code, out = self.cli(env, 'tools.documents.read_docs', '--org', 'testorg', 'reports/doc12.txt', success=False)
        self.assertNotEqual(code, 0)
        self.assertFalse(out['ok'])

    def test_recursive_wildcard_double_star(self):
        """Wildcard ** matches across multiple directory segments."""
        env = self.make_config({
            'allow': [
                'strategy/**',
                '**/*.json'
            ]
        })
        
        _, out = self.cli(env, 'tools.documents.list_docs', '--org', 'testorg')
        doc_ids = {d['id'] for d in out['documents']}
        self.assertIn('strategy/q1.md', doc_ids)
        self.assertIn('strategy/2026/annual.md', doc_ids)
        self.assertIn('root.json', doc_ids)
        self.assertNotIn('notes.txt', doc_ids)

    def test_deny_always_overrides_allow(self):
        """deny list takes precedence over allow rules."""
        env = self.make_config({
            'allow': [
                '**/*.md',
            ],
            'deny': [
                'strategy/confidential.md',
                'internal/**',
            ]
        })
        
        _, out = self.cli(env, 'tools.documents.list_docs', '--org', 'testorg')
        doc_ids = {d['id'] for d in out['documents']}
        
        self.assertIn('overview.md', doc_ids)
        self.assertIn('strategy/q1.md', doc_ids)
        self.assertIn('strategy/2026/annual.md', doc_ids)
        self.assertNotIn('strategy/confidential.md', doc_ids)
        self.assertNotIn('internal/secret.md', doc_ids)
        
        # Direct read on confidential.md must fail
        code, out = self.cli(env, 'tools.documents.read_docs', '--org', 'testorg', 'strategy/confidential.md', success=False)
        self.assertNotEqual(code, 0)
        self.assertFalse(out['ok'])
        self.assertIn('denied by policy', out['error'])

    def test_deny_without_allow_list(self):
        """When allow is omitted, all files are permitted except those matching deny."""
        env = self.make_config({
            'deny': [
                'internal/**',
                '*.json',
            ]
        })
        
        _, out = self.cli(env, 'tools.documents.list_docs', '--org', 'testorg')
        doc_ids = {d['id'] for d in out['documents']}
        
        self.assertIn('overview.md', doc_ids)
        self.assertIn('strategy/q1.md', doc_ids)
        self.assertNotIn('internal/secret.md', doc_ids)
        self.assertNotIn('root.json', doc_ids)
        
        # Direct read on root.json must fail
        code, out = self.cli(env, 'tools.documents.read_docs', '--org', 'testorg', 'root.json', success=False)
        self.assertFalse(out['ok'])

    def test_directory_slash_shorthand(self):
        """Patterns ending with / (e.g. internal/) block the directory recursively."""
        env = self.make_config({
            'deny': ['internal/']
        })
        _, out = self.cli(env, 'tools.documents.list_docs', '--org', 'testorg')
        doc_ids = {d['id'] for d in out['documents']}
        self.assertNotIn('internal/secret.md', doc_ids)
        self.assertNotIn('internal/budget.csv', doc_ids)
        self.assertIn('overview.md', doc_ids)

    def test_path_traversal_and_escapes(self):
        """Path traversal outside root is rejected."""
        env = self.make_config(None)
        
        code, out = self.cli(env, 'tools.documents.read_docs', '--org', 'testorg', '../config.yaml', success=False)
        self.assertNotEqual(code, 0)
        self.assertFalse(out['ok'])
        self.assertIn('Path traversal', out['error'])
        
        code, out = self.cli(env, 'tools.documents.read_docs', '--org', 'testorg', 'strategy/../../config.yaml', success=False)
        self.assertNotEqual(code, 0)
        self.assertFalse(out['ok'])
        self.assertIn('Path traversal', out['error'])

    def test_traversal_cannot_bypass_deny_policy(self):
        """Attempting to access a denied file via redundant relative navigation is blocked."""
        env = self.make_config({
            'deny': ['strategy/confidential.md']
        })
        
        code, out = self.cli(env, 'tools.documents.read_docs', '--org', 'testorg', 'strategy/../strategy/confidential.md', success=False)
        self.assertNotEqual(code, 0)
        self.assertFalse(out['ok'])
        self.assertIn('denied by policy', out['error'])

    def test_windows_and_unix_path_consistency(self):
        """Backslashes and forward slashes are treated consistently."""
        env = self.make_config({
            'allow': ['strategy/q1.md']
        })
        
        # Test backslash path
        _, out = self.cli(env, 'tools.documents.read_docs', '--org', 'testorg', 'strategy\\q1.md')
        self.assertTrue(out['ok'])
        self.assertEqual(out['documents'][0]['id'], 'strategy\\q1.md')
        self.assertIn('Q1 Strategy', out['documents'][0]['content'])

if __name__ == '__main__':
    unittest.main()
