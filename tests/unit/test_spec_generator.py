"""
Unit tests for SpecGenerator module.
"""

import unittest
from unittest.mock import patch, MagicMock
from src.agents.spec_generator import SpecGenerator


class TestSpecGenerator(unittest.TestCase):
    """Test cases for SpecGenerator class."""
    
    def test_parse_combat_maneuver_response_with_structured_data(self):
        """Test parsing a well-structured combat maneuver response."""
        response = """
**Error Signature**: AttributeError: 'NoneType' object has no attribute 'find'

**Root Cause**: The HTML parser returned None when trying to find an element that doesn't exist.

**Solution Code**:
```python
element = soup.find('div', class_='content')
if element is not None:
    text = element.get_text()
else:
    text = "Element not found"
```

**Prevention Strategy**: Always check if elements exist before accessing their methods or attributes.
"""
        
        maneuver = SpecGenerator._parse_combat_maneuver_response(response)
        
        self.assertIn("AttributeError", maneuver['error_signature'])
        self.assertIn("HTML parser", maneuver['root_cause'])
        self.assertIn("if element is not None", maneuver['solution_code'])
        self.assertIn("check if elements exist", maneuver['prevention_strategy'])
        self.assertIsNotNone(maneuver['learned_on'])
    
    def test_parse_combat_maneuver_response_without_code_blocks(self):
        """Test parsing when code is not in code blocks."""
        response = """
Error Signature: Connection timeout error

Root Cause: Network latency or server unavailability

Solution Code: Add retry logic with exponential backoff

Prevention Strategy: Implement proper timeout handling
"""
        
        maneuver = SpecGenerator._parse_combat_maneuver_response(response)
        
        self.assertIn("timeout", maneuver['error_signature'].lower())
        self.assertIn("latency", maneuver['root_cause'].lower())
        self.assertIn("retry", maneuver['solution_code'].lower())
        self.assertIn("timeout", maneuver['prevention_strategy'].lower())
    
    def test_parse_combat_maneuver_response_empty(self):
        """Test parsing an empty response."""
        response = ""
        
        maneuver = SpecGenerator._parse_combat_maneuver_response(response)
        
        # Should still return a valid structure with defaults
        self.assertIn('error_signature', maneuver)
        self.assertIn('root_cause', maneuver)
        self.assertIn('solution_code', maneuver)
        self.assertIn('prevention_strategy', maneuver)
        self.assertIn('learned_on', maneuver)
    
    @patch('src.agents.spec_generator.chat_completion')
    def test_generate_specialist_spec_success(self, mock_chat):
        """Test successful specialist spec generation."""
        mock_chat.return_value = "# Specialist: test-library\n\n## Library Info\n..."
        
        result = SpecGenerator.generate_specialist_spec(
            "test-library",
            "Test error",
            "Traceback..."
        )
        
        self.assertIsNotNone(result)
        self.assertIn("Specialist", result)
        mock_chat.assert_called_once()
    
    @patch('src.agents.spec_generator.chat_completion')
    def test_generate_specialist_spec_failure(self, mock_chat):
        """Test specialist spec generation with API failure."""
        mock_chat.side_effect = Exception("API Error")
        
        result = SpecGenerator.generate_specialist_spec(
            "test-library",
            "Test error",
            "Traceback..."
        )
        
        self.assertIsNone(result)
    
    @patch('src.agents.spec_generator.chat_completion')
    def test_generate_combat_maneuver_success(self, mock_chat):
        """Test successful combat maneuver generation."""
        mock_response = """
Error Signature: Test error pattern
Root Cause: Test cause
Solution Code: test_solution()
Prevention Strategy: Test prevention
"""
        mock_chat.return_value = mock_response
        
        result = SpecGenerator.generate_combat_maneuver(
            "test-library",
            "Test error",
            "Traceback...",
            []
        )
        
        self.assertIsNotNone(result)
        self.assertIn('error_signature', result)
        self.assertIn('Test error pattern', result['error_signature'])
        mock_chat.assert_called_once()
    
    @patch('src.agents.spec_generator.chat_completion')
    def test_generate_combat_maneuver_with_existing_maneuvers(self, mock_chat):
        """Test combat maneuver generation with existing maneuvers."""
        mock_chat.return_value = "Error Signature: New error\nRoot Cause: New cause"
        
        existing = [
            {'error_signature': 'Old error 1'},
            {'error_signature': 'Old error 2'}
        ]
        
        result = SpecGenerator.generate_combat_maneuver(
            "test-library",
            "Test error",
            "Traceback...",
            existing
        )
        
        self.assertIsNotNone(result)
        # Verify existing maneuvers were included in the prompt
        call_args = mock_chat.call_args[0][0]
        prompt_text = call_args[1]['content']
        self.assertIn('Old error 1', prompt_text)
        self.assertIn('Old error 2', prompt_text)
    
    @patch('src.agents.spec_generator.chat_completion')
    def test_generate_combat_maneuver_failure(self, mock_chat):
        """Test combat maneuver generation with API failure."""
        mock_chat.side_effect = Exception("API Error")
        
        result = SpecGenerator.generate_combat_maneuver(
            "test-library",
            "Test error",
            "Traceback...",
            []
        )
        
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
