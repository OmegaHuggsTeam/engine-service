"""
Spec Generator Module

This module interfaces with Groq API to generate and evolve specialist specs.
It handles prompt construction, API calls, and response parsing.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.llm_client import chat_completion

logger = logging.getLogger(__name__)


class SpecGenerator:
    """Generates and evolves specialist specs via Groq API."""
    
    CREATION_PROMPT_TEMPLATE = """Based on error [{error}], create a Specialist Agent for [{library}].

The specialist should focus on:
1. Code Injection Security (OWASP guidelines)
2. Memory Efficiency techniques
3. Resilient Monkey Patching strategies

Include the following sections:
- Library Info (name, version compatibility)
- Common Error Patterns (known errors and solutions)
- Security Considerations (injection prevention, sandboxing)
- Memory Efficiency (optimization techniques)
- Monkey Patching Strategies (resilient approaches)
- Combat Maneuvers (empty initially)
- Evolution History (empty initially)

Format as markdown with clear section headers."""
    
    EVOLUTION_PROMPT_TEMPLATE = """The specialist for [{library}] failed to resolve error [{error}].

Analyze the error and generate a new Combat Maneuver with:
1. Error Signature: Pattern that identifies this error
2. Root Cause: Why this error occurs
3. Solution Code: Executable Python code to fix it
4. Prevention Strategy: How to avoid this error

Traceback:
{traceback}

Existing Combat Maneuvers:
{existing_maneuvers}

Generate ONLY the new combat maneuver in markdown format."""
    
    @staticmethod
    def generate_specialist_spec(
        library_name: str,
        error_message: str,
        traceback_str: str
    ) -> Optional[str]:
        """
        Generate a new specialist spec via Groq API.
        
        Args:
            library_name: The normalized library name
            error_message: The error message that triggered creation
            traceback_str: The full exception traceback
            
        Returns:
            The generated spec as markdown, or None if failed
        """
        try:
            # Build the creation prompt
            prompt = SpecGenerator.CREATION_PROMPT_TEMPLATE.format(
                error=error_message,
                library=library_name
            )
            
            # Add traceback context
            full_prompt = f"{prompt}\n\nTraceback:\n{traceback_str}"
            
            # Call Groq API
            messages = [
                {"role": "system", "content": "You are an expert at creating specialist agent specifications for Python libraries. Focus on security, memory efficiency, and resilient error handling."},
                {"role": "user", "content": full_prompt}
            ]
            
            logger.info(f"Generating specialist spec for {library_name} via Groq API")
            response = chat_completion(messages)
            
            if response:
                logger.info(f"Successfully generated specialist spec for {library_name}")
                return response
            else:
                logger.error(f"Empty response from Groq API for {library_name}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to generate specialist spec for {library_name}: {e}")
            return None
    
    @staticmethod
    def generate_combat_maneuver(
        library_name: str,
        error_message: str,
        traceback_str: str,
        existing_maneuvers: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a new combat maneuver via Groq API.
        
        Args:
            library_name: The normalized library name
            error_message: The error message that triggered evolution
            traceback_str: The full exception traceback
            existing_maneuvers: List of existing combat maneuvers
            
        Returns:
            A dictionary containing the new combat maneuver, or None if failed
        """
        try:
            # Format existing maneuvers for context
            maneuvers_text = ""
            if existing_maneuvers:
                for i, maneuver in enumerate(existing_maneuvers, 1):
                    maneuvers_text += f"\n{i}. {maneuver.get('error_signature', 'Unknown')}"
            else:
                maneuvers_text = "None yet"
            
            # Build the evolution prompt
            prompt = SpecGenerator.EVOLUTION_PROMPT_TEMPLATE.format(
                library=library_name,
                error=error_message,
                traceback=traceback_str,
                existing_maneuvers=maneuvers_text
            )
            
            # Call Groq API
            messages = [
                {"role": "system", "content": "You are an expert at analyzing Python library errors and creating combat maneuvers. Provide structured solutions with error signatures, root causes, solution code, and prevention strategies."},
                {"role": "user", "content": prompt}
            ]
            
            logger.info(f"Generating combat maneuver for {library_name} via Groq API")
            response = chat_completion(messages)
            
            if response:
                # Parse the response into a structured combat maneuver
                maneuver = SpecGenerator._parse_combat_maneuver_response(response)
                logger.info(f"Successfully generated combat maneuver for {library_name}")
                return maneuver
            else:
                logger.error(f"Empty response from Groq API for {library_name}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to generate combat maneuver for {library_name}: {e}")
            return None
    
    @staticmethod
    def _parse_combat_maneuver_response(response: str) -> Dict[str, Any]:
        """
        Parse Groq API response into a structured combat maneuver.
        
        Args:
            response: The raw response from Groq API
            
        Returns:
            A dictionary with combat maneuver fields
        """
        import re
        
        # Initialize with defaults
        maneuver = {
            'error_signature': '',
            'root_cause': '',
            'solution_code': '',
            'prevention_strategy': '',
            'learned_on': datetime.now().isoformat()
        }
        
        try:
            # Extract Error Signature
            error_sig_match = re.search(
                r'(?:Error Signature|error signature)[:\s]*\*?\*?(.+?)(?=\n\n|\n-|\n\*\*|Root Cause|$)',
                response,
                re.IGNORECASE | re.DOTALL
            )
            if error_sig_match:
                maneuver['error_signature'] = error_sig_match.group(1).strip().strip('*').strip()
            
            # Extract Root Cause
            root_cause_match = re.search(
                r'(?:Root Cause|root cause)[:\s]*\*?\*?(.+?)(?=\n\n|\n-|\n\*\*|Solution Code|$)',
                response,
                re.IGNORECASE | re.DOTALL
            )
            if root_cause_match:
                maneuver['root_cause'] = root_cause_match.group(1).strip().strip('*').strip()
            
            # Extract Solution Code (look for code blocks)
            code_match = re.search(
                r'```(?:python)?\s*\n(.*?)\n```',
                response,
                re.DOTALL
            )
            if code_match:
                maneuver['solution_code'] = code_match.group(1).strip()
            else:
                # Try to find solution code section without code blocks
                solution_match = re.search(
                    r'(?:Solution Code|solution code)[:\s]*\*?\*?(.+?)(?=\n\n|\n-|\n\*\*|Prevention Strategy|$)',
                    response,
                    re.IGNORECASE | re.DOTALL
                )
                if solution_match:
                    maneuver['solution_code'] = solution_match.group(1).strip().strip('*').strip()
            
            # Extract Prevention Strategy
            prevention_match = re.search(
                r'(?:Prevention Strategy|prevention strategy)[:\s]*\*?\*?(.+?)(?=\n\n|\n-|\n\*\*|$)',
                response,
                re.IGNORECASE | re.DOTALL
            )
            if prevention_match:
                maneuver['prevention_strategy'] = prevention_match.group(1).strip().strip('*').strip()
            
            # If we couldn't extract structured fields, use the whole response as error signature
            if not any([maneuver['error_signature'], maneuver['root_cause'], maneuver['solution_code']]):
                maneuver['error_signature'] = response[:200] + '...' if len(response) > 200 else response
                logger.warning("Could not parse structured combat maneuver, using raw response")
                
        except Exception as e:
            logger.error(f"Error parsing combat maneuver response: {e}")
            maneuver['error_signature'] = "Parse error - see raw response"
            maneuver['root_cause'] = str(e)
        
        return maneuver
