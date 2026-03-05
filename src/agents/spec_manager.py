"""
Spec Manager Module

This module handles file I/O operations for specialist specs, including loading,
saving, updating, and parsing markdown spec files.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class SpecManager:
    """Manages specialist spec files on disk."""
    
    SPECS_DIR = Path("src/agents/specs")
    
    @staticmethod
    def spec_exists(library_name: str) -> bool:
        """
        Check if a specialist spec file exists for the given library.
        
        Args:
            library_name: The normalized library name
            
        Returns:
            True if the spec file exists, False otherwise
        """
        spec_path = SpecManager.SPECS_DIR / f"{library_name}.md"
        return spec_path.exists()
    
    @staticmethod
    def load_spec(library_name: str) -> Optional[Dict[str, Any]]:
        """
        Load and parse a specialist spec from disk.
        
        Args:
            library_name: The normalized library name
            
        Returns:
            A dictionary containing the parsed spec, or None if not found
        """
        spec_path = SpecManager.SPECS_DIR / f"{library_name}.md"
        
        if not spec_path.exists():
            return None
        
        try:
            content = spec_path.read_text(encoding='utf-8')
            parsed_spec = SpecManager._parse_spec_markdown(content)
            
            # Validate the parsed spec
            if not SpecManager._validate_spec(parsed_spec):
                print(f"Spec validation failed for {library_name}")
                return None
            
            return parsed_spec
        except Exception as e:
            # Log error and return None
            print(f"Error loading spec for {library_name}: {e}")
            return None
    
    @staticmethod
    def save_spec(library_name: str, content: str) -> bool:
        """
        Save a specialist spec to disk.
        
        Args:
            library_name: The normalized library name
            content: The markdown content to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure specs directory exists
            SpecManager.SPECS_DIR.mkdir(parents=True, exist_ok=True)
            
            spec_path = SpecManager.SPECS_DIR / f"{library_name}.md"
            spec_path.write_text(content, encoding='utf-8')
            return True
        except Exception as e:
            print(f"Error saving spec for {library_name}: {e}")
            return False
    
    @staticmethod
    def update_spec(
        library_name: str,
        new_combat_maneuver: Dict[str, Any],
        evolution_entry: Dict[str, Any]
    ) -> bool:
        """
        Update an existing spec with a new combat maneuver and evolution entry.
        
        Args:
            library_name: The normalized library name
            new_combat_maneuver: The new combat maneuver to append
            evolution_entry: The evolution history entry to append
            
        Returns:
            True if successful, False otherwise
        """
        spec_path = SpecManager.SPECS_DIR / f"{library_name}.md"
        
        if not spec_path.exists():
            return False
        
        try:
            content = spec_path.read_text(encoding='utf-8')
            
            # Format the new combat maneuver
            maneuver_md = SpecManager._format_combat_maneuver(new_combat_maneuver)
            
            # Format the evolution entry
            evolution_md = f"- **{evolution_entry['timestamp']}**: {evolution_entry['error_type']} - {evolution_entry['solution_summary']}\n"
            
            # Find and append to Combat Maneuvers section
            combat_section_pattern = r'(## Combat Maneuvers\s*\n)'
            if re.search(combat_section_pattern, content):
                content = re.sub(
                    combat_section_pattern,
                    r'\1' + maneuver_md + '\n',
                    content,
                    count=1
                )
            else:
                # If section doesn't exist, add it before Evolution History
                content = content.replace(
                    '## Evolution History',
                    f'## Combat Maneuvers\n\n{maneuver_md}\n\n## Evolution History'
                )
            
            # Find and append to Evolution History section
            evolution_section_pattern = r'(## Evolution History\s*\n)'
            if re.search(evolution_section_pattern, content):
                content = re.sub(
                    evolution_section_pattern,
                    r'\1' + evolution_md,
                    content,
                    count=1
                )
            else:
                # If section doesn't exist, add it at the end
                content += f'\n## Evolution History\n\n{evolution_md}'
            
            # Save updated content
            spec_path.write_text(content, encoding='utf-8')
            return True
        except Exception as e:
            print(f"Error updating spec for {library_name}: {e}")
            return False
    
    @staticmethod
    def _validate_spec(spec: Dict[str, Any]) -> bool:
        """
        Validate that a parsed spec contains all required sections.
        
        Args:
            spec: The parsed spec dictionary
            
        Returns:
            True if valid, False otherwise
        """
        required_keys = [
            'library_name',
            'version_compatibility',
            'error_patterns',
            'security_considerations',
            'memory_efficiency',
            'monkey_patching',
            'combat_maneuvers',
            'evolution_history'
        ]
        
        # Check all required keys exist
        for key in required_keys:
            if key not in spec:
                print(f"Missing required key: {key}")
                return False
        
        # Check library_name is not empty
        if not spec['library_name']:
            print("Library name is empty")
            return False
        
        return True
    
    @staticmethod
    def _parse_spec_markdown(content: str) -> Dict[str, Any]:
        """
        Parse markdown spec content into a structured dictionary.
        
        Args:
            content: The markdown content
            
        Returns:
            A dictionary with parsed sections
        """
        spec = {
            'library_name': '',
            'version_compatibility': '',
            'error_patterns': [],
            'security_considerations': '',
            'memory_efficiency': '',
            'monkey_patching': '',
            'combat_maneuvers': [],
            'evolution_history': []
        }
        
        # Extract library name from title
        title_match = re.search(r'#\s+Specialist:\s+(.+)', content)
        if title_match:
            spec['library_name'] = title_match.group(1).strip()
        
        # Extract version compatibility
        version_match = re.search(r'\*\*Version Compatibility\*\*:\s*(.+)', content)
        if version_match:
            spec['version_compatibility'] = version_match.group(1).strip()
        
        # Extract sections
        sections = {
            'security_considerations': r'## Security Considerations\s*\n(.*?)(?=\n##|\Z)',
            'memory_efficiency': r'## Memory Efficiency\s*\n(.*?)(?=\n##|\Z)',
            'monkey_patching': r'## Monkey Patching Strategies\s*\n(.*?)(?=\n##|\Z)',
        }
        
        for key, pattern in sections.items():
            match = re.search(pattern, content, re.DOTALL)
            if match:
                spec[key] = match.group(1).strip()
        
        # Parse combat maneuvers
        combat_section = re.search(
            r'## Combat Maneuvers\s*\n(.*?)(?=\n##|\Z)',
            content,
            re.DOTALL
        )
        if combat_section:
            maneuvers_text = combat_section.group(1)
            spec['combat_maneuvers'] = SpecManager._parse_combat_maneuvers(maneuvers_text)
        
        # Parse evolution history
        evolution_section = re.search(
            r'## Evolution History\s*\n(.*?)(?=\Z)',
            content,
            re.DOTALL
        )
        if evolution_section:
            history_text = evolution_section.group(1)
            spec['evolution_history'] = SpecManager._parse_evolution_history(history_text)
        
        return spec
    
    @staticmethod
    def _parse_combat_maneuvers(text: str) -> List[Dict[str, Any]]:
        """Parse combat maneuvers from markdown text."""
        maneuvers = []
        
        # Split by maneuver headers (### Maneuver N: or ### Maneuver:)
        maneuver_blocks = re.split(r'###\s+Maneuver(?:\s+\d+)?:', text)
        
        for block in maneuver_blocks[1:]:  # Skip first empty split
            maneuver = {}
            
            # Extract title
            title_match = re.search(r'^(.+?)\n', block)
            if title_match:
                maneuver['title'] = title_match.group(1).strip()
            
            # Extract fields
            error_sig = re.search(r'\*\*Error Signature\*\*:\s*(.+?)(?=\n-|\n\n|\Z)', block, re.DOTALL)
            if error_sig:
                maneuver['error_signature'] = error_sig.group(1).strip()
            
            root_cause = re.search(r'\*\*Root Cause\*\*:\s*(.+?)(?=\n-|\n\n|\Z)', block, re.DOTALL)
            if root_cause:
                maneuver['root_cause'] = root_cause.group(1).strip()
            
            solution = re.search(r'\*\*Solution Code\*\*:\s*\n```python\n(.*?)```', block, re.DOTALL)
            if solution:
                maneuver['solution_code'] = solution.group(1).strip()
            
            prevention = re.search(r'\*\*Prevention Strategy\*\*:\s*(.+?)(?=\n-|\n\n|\Z)', block, re.DOTALL)
            if prevention:
                maneuver['prevention_strategy'] = prevention.group(1).strip()
            
            learned_on = re.search(r'\*\*Learned On\*\*:\s*(.+)', block)
            if learned_on:
                maneuver['learned_on'] = learned_on.group(1).strip()
            
            if maneuver:
                maneuvers.append(maneuver)
        
        return maneuvers
    
    @staticmethod
    def _parse_evolution_history(text: str) -> List[Dict[str, Any]]:
        """Parse evolution history from markdown text."""
        history = []
        
        # Match lines like: - **timestamp**: error_type - solution_summary
        entries = re.findall(r'-\s+\*\*(.+?)\*\*:\s+(.+?)\s+-\s+(.+)', text)
        
        for timestamp, error_type, solution_summary in entries:
            history.append({
                'timestamp': timestamp.strip(),
                'error_type': error_type.strip(),
                'solution_summary': solution_summary.strip()
            })
        
        return history
    
    @staticmethod
    def _format_combat_maneuver(maneuver: Dict[str, Any]) -> str:
        """
        Format a combat maneuver dictionary as markdown.
        
        Args:
            maneuver: The combat maneuver dictionary
            
        Returns:
            Formatted markdown string
        """
        title = maneuver.get('title', 'Untitled Maneuver')
        error_sig = maneuver.get('error_signature', 'N/A')
        root_cause = maneuver.get('root_cause', 'N/A')
        solution = maneuver.get('solution_code', '# No solution provided')
        prevention = maneuver.get('prevention_strategy', 'N/A')
        learned_on = maneuver.get('learned_on', datetime.now().isoformat())
        
        return f"""### Maneuver: {title}
- **Error Signature**: {error_sig}
- **Root Cause**: {root_cause}
- **Solution Code**:
```python
{solution}
```
- **Prevention Strategy**: {prevention}
- **Learned On**: {learned_on}
"""
