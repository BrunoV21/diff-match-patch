"""Test suite for V4A-Compatible patch applier."""

import os
import shutil
import tempfile
import unittest
from typing import List, Tuple

from diff_match_patch.patch_applier import PatchApplier


class TestPatchApplier(unittest.TestCase):
    """Test cases for PatchApplier class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.applier = PatchApplier()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temp directory
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_parse_patch_empty(self):
        """Test parsing empty patch."""
        result = self.applier.parse_patch("")
        self.assertEqual(result, [])
        
        result = self.applier.parse_patch("   \n  \n  ")
        self.assertEqual(result, [])
    
    def test_parse_patch_update_action(self):
        """Test parsing Update action patch."""
        patch_text = """*** Begin Patch
*** Update File: test.py
@@ def hello():
 context1
 context2
 context3
- old_line
+ new_line
 context4
 context5
 context6
*** End Patch"""
        
        blocks = self.applier.parse_patch(patch_text)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]['action'], 'Update')
        self.assertEqual(blocks[0]['file_path'], 'test.py')
        self.assertEqual(len(blocks[0]['hunks']), 1)
        
        hunk = blocks[0]['hunks'][0]
        self.assertEqual(hunk['header'], 'def hello():')
        self.assertEqual(len(hunk['lines']), 7)
        
        # Verify line prefixes and content
        expected_lines = [
            (' ', 'context1'),
            (' ', 'context2'),
            (' ', 'context3'),
            ('-', 'old_line'),
            ('+', 'new_line'),
            (' ', 'context4'),
            (' ', 'context5'),
            (' ', 'context6')
        ]
        
        for i, (prefix, content) in enumerate(expected_lines[:3]):
            self.assertEqual(hunk['lines'][i], (prefix, content))
    
    def test_parse_patch_add_action(self):
        """Test parsing Add action patch."""
        patch_text = """*** Begin Patch
*** Add File: new_file.py
+ def new_function():
+     return "Hello"
+ 
+ class NewClass:
+     pass
*** End Patch"""
        
        blocks = self.applier.parse_patch(patch_text)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]['action'], 'Add')
        self.assertEqual(blocks[0]['file_path'], 'new_file.py')
        self.assertEqual(len(blocks[0]['content']), 5)
        
        expected_content = [
            'def new_function():',
            '    return "Hello"',
            '',
            'class NewClass:',
            '    pass'
        ]
        self.assertEqual(blocks[0]['content'], expected_content)
    
    def test_parse_patch_delete_action(self):
        """Test parsing Delete action patch."""
        patch_text = """*** Begin Patch
*** Delete File: old_file.py
*** End Patch"""
        
        blocks = self.applier.parse_patch(patch_text)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]['action'], 'Delete')
        self.assertEqual(blocks[0]['file_path'], 'old_file.py')
        self.assertEqual(blocks[0]['hunks'], [])
        self.assertEqual(blocks[0]['content'], [])
    
    def test_parse_patch_multiple_blocks(self):
        """Test parsing multiple patch blocks."""
        patch_text = """*** Begin Patch
*** Update File: file1.py
@@ def func1():
 line1
 line2
 line3
- old
+ new
 line4
 line5
 line6
*** End Patch

*** Begin Patch
*** Add File: file2.py
+ new content
*** End Patch

*** Begin Patch
*** Delete File: file3.py
*** End Patch"""
        
        blocks = self.applier.parse_patch(patch_text)
        self.assertEqual(len(blocks), 3)
        
        self.assertEqual(blocks[0]['action'], 'Update')
        self.assertEqual(blocks[0]['file_path'], 'file1.py')
        
        self.assertEqual(blocks[1]['action'], 'Add')
        self.assertEqual(blocks[1]['file_path'], 'file2.py')
        
        self.assertEqual(blocks[2]['action'], 'Delete')
        self.assertEqual(blocks[2]['file_path'], 'file3.py')
    
    def test_apply_patch_update(self):
        """Test applying an update patch."""
        # Create test file
        test_file = os.path.join(self.temp_dir, 'test.txt')
        original_content = """line1
line2
line3
old_line
line4
line5
line6"""
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(original_content)
        
        # Apply update patch
        patch_text = """*** Begin Patch
*** Update File: test.txt
@@ line1
 line1
 line2
 line3
- old_line
+ new_line
 line4
 line5
 line6
*** End Patch"""
        
        results = self.applier.apply_patch(patch_text, self.temp_dir)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], 'test.txt')
        self.assertTrue(results[0][1])
        
        # Verify file was updated
        with open(test_file, 'r', encoding='utf-8') as f:
            updated_content = f.read()
        
        expected_content = """line1
line2
line3
new_line
line4
line5
line6"""
        self.assertEqual(updated_content, expected_content)
    
    def test_apply_patch_add(self):
        """Test applying an add patch."""
        patch_text = """*** Begin Patch
*** Add File: test_new.txt
+ Line 1
+ Line 2
+ Line 3
*** End Patch"""
        
        results = self.applier.apply_patch(patch_text, self.temp_dir)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], 'test_new.txt')
        self.assertTrue(results[0][1])
        
        # Verify file was created
        test_file = os.path.join(self.temp_dir, 'test_new.txt')
        self.assertTrue(os.path.exists(test_file))
        
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        expected_content = "Line 1\nLine 2\nLine 3"
        self.assertEqual(content, expected_content)
    
    def test_apply_patch_add_with_subdirectory(self):
        """Test applying an add patch that creates subdirectories."""
        patch_text = """*** Begin Patch
*** Add File: subdir/nested/new_file.py
+ def hello():
+     return "world"
*** End Patch"""
        
        results = self.applier.apply_patch(patch_text, self.temp_dir)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0][1])
        
        # Verify file and directories were created
        test_file = os.path.join(self.temp_dir, 'subdir', 'nested', 'new_file.py')
        self.assertTrue(os.path.exists(test_file))
        
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        expected_content = 'def hello():\n    return "world"'
        self.assertEqual(content, expected_content)
    
    def test_apply_patch_delete(self):
        """Test applying a delete patch."""
        # Create file to delete
        test_file = os.path.join(self.temp_dir, 'to_delete.txt')
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("This file will be deleted")
        
        self.assertTrue(os.path.exists(test_file))
        
        # Apply delete patch
        patch_text = """*** Begin Patch
*** Delete File: to_delete.txt
*** End Patch"""
        
        results = self.applier.apply_patch(patch_text, self.temp_dir)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], 'to_delete.txt')
        self.assertTrue(results[0][1])
        
        # Verify file was deleted
        self.assertFalse(os.path.exists(test_file))
    
    def test_apply_patch_delete_nonexistent(self):
        """Test applying a delete patch to a non-existent file."""
        patch_text = """*** Begin Patch
*** Delete File: nonexistent.txt
*** End Patch"""
        
        results = self.applier.apply_patch(patch_text, self.temp_dir)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], 'nonexistent.txt')
        self.assertFalse(results[0][1])
    
    def test_apply_patch_multiple_hunks(self):
        """Test applying patch with multiple hunks."""
        # Create test file
        test_file = os.path.join(self.temp_dir, 'multi.py')
        original_content = """def func1():
    line1
    line2
    old1
    line3
    line4

def func2():
    lineA
    lineB
    old2
    lineC
    lineD"""
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(original_content)
        
        # Apply patch with multiple hunks
        patch_text = """*** Begin Patch
*** Update File: multi.py
@@ def func1():
 def func1():
     line1
     line2
-     old1
+     new1
     line3
     line4

@@ def func2():
 def func2():
     lineA
     lineB
-     old2
+     new2
     lineC
     lineD
*** End Patch"""
        
        results = self.applier.apply_patch(patch_text, self.temp_dir)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0][1])
        
        # Verify both hunks were applied
        with open(test_file, 'r', encoding='utf-8') as f:
            updated_content = f.read()
        
        self.assertIn('new1', updated_content)
        self.assertIn('new2', updated_content)
        self.assertNotIn('old1', updated_content)
        self.assertNotIn('old2', updated_content)
    
    def test_apply_patch_with_context_matching(self):
        """Test context matching in patch application."""
        # Create test file
        test_file = os.path.join(self.temp_dir, 'context.txt')
        original_content = """header
context1
context2
context3
target_line
context4
context5
context6
footer"""
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(original_content)
        
        # Apply patch with specific context
        patch_text = """*** Begin Patch
*** Update File: context.txt
@@ context1
 context1
 context2
 context3
- target_line
+ modified_line
 context4
 context5
 context6
*** End Patch"""
        
        results = self.applier.apply_patch(patch_text, self.temp_dir)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0][1])
        
        # Verify correct line was modified
        with open(test_file, 'r', encoding='utf-8') as f:
            updated_content = f.read()
        
        lines = updated_content.split('\n')
        self.assertEqual(lines[0], 'header')
        self.assertEqual(lines[4], 'modified_line')
        self.assertEqual(lines[8], 'footer')
    
    def test_apply_patch_invalid_format(self):
        """Test handling of invalid patch format."""
        # Missing Begin Patch
        patch_text = """*** Update File: test.txt
@@ line1
 line1
- old
+ new
*** End Patch"""
        
        results = self.applier.apply_patch(patch_text, self.temp_dir)
        self.assertEqual(len(results), 0)
        
        # Missing End Patch
        patch_text = """*** Begin Patch
*** Update File: test.txt
@@ line1
 line1
- old
+ new"""
        
        blocks = self.applier.parse_patch(patch_text)
        # Should still parse but might not have complete info
        self.assertIsInstance(blocks, list)
        
        # Invalid action
        patch_text = """*** Begin Patch
*** Invalid File: test.txt
*** End Patch"""
        
        blocks = self.applier.parse_patch(patch_text)
        self.assertEqual(len(blocks), 0)
    
    def test_hunk_header_validation(self):
        """Test validation of hunk headers."""
        # Create test file
        test_file = os.path.join(self.temp_dir, 'header.txt')
        original_content = """line1
line2
line3
line4
line5"""
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(original_content)
        
        # Patch with valid header
        patch_text = """*** Begin Patch
*** Update File: header.txt
@@ line1
 line1
 line2
 line3
- line4
+ modified4
 line5
*** End Patch"""
        
        blocks = self.applier.parse_patch(patch_text)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]['hunks'][0]['header'], 'line1')
    
    def test_line_prefix_handling(self):
        """Test handling of line prefixes (space, -, +)."""
        patch_text = """*** Begin Patch
*** Update File: prefix_test.py
@@ def test():
 def test():
     # Context line with space prefix
     unchanged_line()
-     removed_line()
+     added_line()
     # Another context line
     more_context()
     final_context()
*** End Patch"""
        
        blocks = self.applier.parse_patch(patch_text)
        self.assertEqual(len(blocks), 1)
        
        hunk = blocks[0]['hunks'][0]
        lines = hunk['lines']
        
        # Check that we have the right prefixes
        prefixes = [line[0] for line in lines]
        self.assertIn(' ', prefixes)  # Context lines
        self.assertIn('-', prefixes)  # Removed line
        self.assertIn('+', prefixes)  # Added line
        
        # Verify specific lines
        for prefix, content in lines:
            if prefix == '-':
                self.assertIn('removed_line', content)
            elif prefix == '+':
                self.assertIn('added_line', content)
    
    def test_apply_multiple_patches_in_sequence(self):
        """Test applying multiple patches to different files."""
        # Create first file
        file1 = os.path.join(self.temp_dir, 'file1.txt')
        with open(file1, 'w', encoding='utf-8') as f:
            f.write("original content")
        
        # Combined patch
        patch_text = """*** Begin Patch
*** Update File: file1.txt
@@ original content
- original content
+ updated content
*** End Patch

*** Begin Patch
*** Add File: file2.txt
+ new file content
*** End Patch

*** Begin Patch
*** Delete File: file1.txt
*** End Patch"""
        
        results = self.applier.apply_patch(patch_text, self.temp_dir)
        self.assertEqual(len(results), 3)
        
        # First patch should update file1
        self.assertEqual(results[0][0], 'file1.txt')
        self.assertTrue(results[0][1])
        
        # Second patch should add file2
        self.assertEqual(results[1][0], 'file2.txt')
        self.assertTrue(results[1][1])
        
        # Third patch should delete file1
        self.assertEqual(results[2][0], 'file1.txt')
        self.assertTrue(results[2][1])
        
        # Verify final state
        self.assertFalse(os.path.exists(file1))
        file2 = os.path.join(self.temp_dir, 'file2.txt')
        self.assertTrue(os.path.exists(file2))
    
    def test_empty_file_handling(self):
        """Test handling of empty files in patches."""
        # Test adding an empty file
        patch_text = """*** Begin Patch
*** Add File: empty.txt
*** End Patch"""
        
        results = self.applier.apply_patch(patch_text, self.temp_dir)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0][1])
        
        empty_file = os.path.join(self.temp_dir, 'empty.txt')
        self.assertTrue(os.path.exists(empty_file))
        
        with open(empty_file, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertEqual(content, '')
    
    def test_whitespace_preservation(self):
        """Test that whitespace is preserved correctly."""
        patch_text = """*** Begin Patch
*** Add File: whitespace.py
+ def function():
+     # Indented comment
+     if True:
+         pass
+ 	# Tab character
+     
+     # Empty line above
*** End Patch"""
        
        results = self.applier.apply_patch(patch_text, self.temp_dir)
        self.assertTrue(results[0][1])
        
        test_file = os.path.join(self.temp_dir, 'whitespace.py')
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check that indentation is preserved
        lines = content.split('\n')
        self.assertTrue(lines[1].startswith('    '))  # 4 spaces
        self.assertTrue(lines[2].startswith('    '))  # 4 spaces
        self.assertTrue(lines[3].startswith('        '))  # 8 spaces


if __name__ == "__main__":
    unittest.main()