"""V4A-Compatible patch format parser and applier.

Handles patch blocks with Update, Add, and Delete actions following the
V4A-Compatible format specification.
"""

import os
import re
from typing import List, Tuple, Optional, Dict, Any


class PatchBlock:
    """Represents a single patch block with action, file path, and content."""
    
    def __init__(self, action: str, file_path: str):
        """Initialize a patch block.
        
        Args:
            action: The action type (Update, Add, Delete).
            file_path: The file path to operate on.
        """
        self.action = action
        self.file_path = file_path
        self.hunks: List[Dict[str, Any]] = []
        self.content: List[str] = []
    
    def add_hunk(self, header: str, lines: List[Tuple[str, str]]):
        """Add a hunk to an Update block.
        
        Args:
            header: The hunk header line (context line from original).
            lines: List of (prefix, line) tuples.
        """
        self.hunks.append({
            'header': header,
            'lines': lines
        })
    
    def add_content_line(self, line: str):
        """Add a content line for Add action.
        
        Args:
            line: The line to add (without prefix).
        """
        self.content.append(line)


class PatchApplier:
    """Applies patches in V4A-Compatible format to files."""
    
    def __init__(self):
        """Initialize the patch applier."""
        self.blocks: List[PatchBlock] = []
    
    def parse_patch(self, patch_text: str) -> List[Dict[str, Any]]:
        """Parse V4A-Compatible patch format into structured blocks.
        
        Args:
            patch_text: The patch text in V4A-Compatible format.
            
        Returns:
            List of patch blocks with action, file path, and content.
        """
        if not patch_text.strip():
            return []
        
        blocks = []
        lines = patch_text.split('\n')
        i = 0
        
        while i < len(lines):
            # Look for patch block start
            if lines[i].strip() == '*** Begin Patch':
                i += 1
                block = self._parse_block(lines, i)
                if block:
                    blocks.append(block)
                    i = block['end_index'] + 1
                else:
                    i += 1
            else:
                i += 1
        
        return blocks
    
    def _parse_block(self, lines: List[str], start_idx: int) -> Optional[Dict[str, Any]]:
        """Parse a single patch block.
        
        Args:
            lines: All lines of the patch.
            start_idx: Starting index for this block.
            
        Returns:
            Dictionary representing the patch block or None if invalid.
        """
        i = start_idx
        
        # Find action line
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('*** Update File:'):
                action = 'Update'
                file_path = line[len('*** Update File:'):].strip()
                break
            elif line.startswith('*** Add File:'):
                action = 'Add'
                file_path = line[len('*** Add File:'):].strip()
                break
            elif line.startswith('*** Delete File:'):
                action = 'Delete'
                file_path = line[len('*** Delete File:'):].strip()
                break
            elif line == '*** End Patch':
                return None
            i += 1
        else:
            return None
        
        i += 1
        
        # Parse content based on action
        if action == 'Delete':
            # Delete has no content, just find end
            while i < len(lines) and lines[i].strip() != '*** End Patch':
                i += 1
            return {
                'action': action,
                'file_path': file_path,
                'hunks': [],
                'content': [],
                'end_index': i
            }
        elif action == 'Add':
            # Parse Add content
            content = []
            while i < len(lines) and lines[i].strip() != '*** End Patch':
                if lines[i].startswith('+'):
                    content.append(lines[i][1:])
                i += 1
            return {
                'action': action,
                'file_path': file_path,
                'hunks': [],
                'content': content,
                'end_index': i
            }
        else:  # Update
            # Parse Update hunks
            hunks = []
            while i < len(lines) and lines[i].strip() != '*** End Patch':
                if lines[i].startswith('@@'):
                    hunk = self._parse_hunk(lines, i)
                    if hunk:
                        hunks.append(hunk)
                        i = hunk['end_index'] + 1
                    else:
                        i += 1
                else:
                    i += 1
            
            return {
                'action': action,
                'file_path': file_path,
                'hunks': hunks,
                'content': [],
                'end_index': i
            }
    
    def _parse_hunk(self, lines: List[str], start_idx: int) -> Optional[Dict[str, Any]]:
        """Parse a single hunk in an Update block.
        
        Args:
            lines: All lines of the patch.
            start_idx: Starting index for this hunk.
            
        Returns:
            Dictionary representing the hunk or None if invalid.
        """
        if not lines[start_idx].startswith('@@'):
            return None
        
        # Extract header (context line)
        header = lines[start_idx][2:].strip()
        
        i = start_idx + 1
        hunk_lines = []
        
        # Parse hunk lines
        while i < len(lines):
            line = lines[i]
            
            # Check for end conditions
            if line.strip() == '*** End Patch':
                break
            if line.startswith('@@'):
                # Start of next hunk
                i -= 1
                break
            
            # Parse line based on prefix
            if line.startswith(' '):
                # Context line
                hunk_lines.append((' ', line[1:]))
            elif line.startswith('-'):
                # Removed line
                hunk_lines.append(('-', line[1:]))
            elif line.startswith('+'):
                # Added line
                hunk_lines.append(('+', line[1:]))
            else:
                # Might be end of hunk
                break
            
            i += 1
        
        return {
            'header': header,
            'lines': hunk_lines,
            'end_index': i - 1
        }
    
    def apply_patch(self, patch_text: str, base_dir: str = ".") -> List[Tuple[str, bool, str]]:
        """Apply a V4A-Compatible patch to files.
        
        Args:
            patch_text: The patch text to apply.
            base_dir: Base directory for file operations.
            
        Returns:
            List of (file_path, success, message) tuples.
        """
        blocks = self.parse_patch(patch_text)
        results = []
        
        for block in blocks:
            file_path = os.path.join(base_dir, block['file_path'])
            
            try:
                if block['action'] == 'Update':
                    success = self._apply_update(file_path, block['hunks'])
                    message = "Updated successfully" if success else "Failed to apply update"
                elif block['action'] == 'Add':
                    success = self._apply_add(file_path, block['content'])
                    message = "Added successfully" if success else "Failed to add file"
                elif block['action'] == 'Delete':
                    success = self._apply_delete(file_path)
                    message = "Deleted successfully" if success else "Failed to delete file"
                else:
                    success = False
                    message = f"Unknown action: {block['action']}"
                
                results.append((block['file_path'], success, message))
            except Exception as e:
                results.append((block['file_path'], False, str(e)))
        
        return results
    
    def _apply_update(self, file_path: str, hunks: List[Dict[str, Any]]) -> bool:
        """Apply update hunks to an existing file.
        
        Args:
            file_path: Path to the file to update.
            hunks: List of hunks with context and changes.
            
        Returns:
            True if successful, False otherwise.
        """
        if not os.path.exists(file_path):
            return False
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # Apply hunks in reverse order to maintain line numbers
            for hunk in reversed(hunks):
                lines = self._apply_hunk_to_lines(lines, hunk)
                if lines is None:
                    return False
            
            # Write updated content back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            return True
        except Exception:
            return False
    
    def _apply_hunk_to_lines(self, lines: List[str], hunk: Dict[str, Any]) -> Optional[List[str]]:
        """Apply a single hunk to lines.
        
        Args:
            lines: Current file lines.
            hunk: Hunk to apply.
            
        Returns:
            Updated lines or None if failed.
        """
        header = hunk['header']
        hunk_lines = hunk['lines']
        
        # Find the location to apply the hunk by matching the header line
        match_idx = -1
        for i, line in enumerate(lines):
            if line.strip() == header.strip():
                match_idx = i
                break
        
        if match_idx == -1:
            # Try to find by context matching
            match_idx = self._find_hunk_location(lines, hunk_lines)
            if match_idx == -1:
                return None
        
        # Build the context and changes
        context_before = []
        context_after = []
        removals = []
        additions = []
        
        in_changes = False
        for prefix, line in hunk_lines:
            if prefix == ' ':
                if in_changes:
                    context_after.append(line)
                else:
                    context_before.append(line)
            elif prefix == '-':
                in_changes = True
                removals.append(line)
            elif prefix == '+':
                in_changes = True
                additions.append(line)
        
        # Calculate the start position
        start_idx = match_idx - len(context_before) + 1
        if start_idx < 0:
            start_idx = 0
        
        # Verify context matches
        expected_lines = context_before + removals + context_after
        actual_lines = lines[start_idx:start_idx + len(expected_lines)]
        
        # Build new lines
        new_lines = lines[:start_idx]
        new_lines.extend(context_before)
        new_lines.extend(additions)
        new_lines.extend(context_after)
        new_lines.extend(lines[start_idx + len(context_before) + len(removals) + len(context_after):])
        
        return new_lines
    
    def _find_hunk_location(self, lines: List[str], hunk_lines: List[Tuple[str, str]]) -> int:
        """Find where to apply a hunk by matching context.
        
        Args:
            lines: File lines.
            hunk_lines: Hunk lines with prefixes.
            
        Returns:
            Index where hunk should be applied or -1 if not found.
        """
        # Extract context lines for matching
        context_lines = []
        for prefix, line in hunk_lines:
            if prefix == ' ':
                context_lines.append(line)
            elif prefix == '-':
                context_lines.append(line)
            else:
                break
        
        if not context_lines:
            return -1
        
        # Try to find matching context
        for i in range(len(lines) - len(context_lines) + 1):
            match = True
            for j, ctx_line in enumerate(context_lines):
                if lines[i + j].strip() != ctx_line.strip():
                    match = False
                    break
            if match:
                return i
        
        return -1
    
    def _apply_add(self, file_path: str, content: List[str]) -> bool:
        """Create a new file with the given content.
        
        Args:
            file_path: Path for the new file.
            content: Content lines to write to the file.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Create directories if needed
            dir_path = os.path.dirname(file_path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path)
            
            # Write content to new file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
            
            return True
        except Exception:
            return False
    
    def _apply_delete(self, file_path: str) -> bool:
        """Delete an existing file.
        
        Args:
            file_path: Path to the file to delete.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False