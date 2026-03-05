"""
Agent Factory Module

This module orchestrates the entire specialist workflow: identifying libraries from
exceptions, checking for existing specialists, creating new ones, loading and applying
specialist knowledge, and evolving specialists when errors persist.
"""

import logging
from typing import Any, Dict, Optional

from .traceback_analyzer import TracebackAnalyzer
from .spec_manager import SpecManager
from .spec_generator import SpecGenerator


# Configure logging
logger = logging.getLogger(__name__)


class AgentFactory:
    """Factory for creating and managing specialist agents."""
    
    @staticmethod
    def handle_exception(
        exception: Exception,
        traceback_str: str
    ) -> Dict[str, Any]:
        """
        Main entry point for exception handling with specialist agents.
        
        This method orchestrates the full workflow:
        1. Identify the library from the traceback
        2. Check if a specialist exists
        3. Create a new specialist if needed
        4. Load and apply specialist knowledge
        5. Evolve the specialist if the error persists
        
        Args:
            exception: The exception that occurred
            traceback_str: The full exception traceback as a string
            
        Returns:
            A dictionary containing:
                - specialist_name: The library name (or None)
                - specialist_exists: Whether a specialist was found
                - combat_maneuvers_applied: List of maneuver titles applied
                - evolution_triggered: Whether evolution was needed
                - suggested_solution: The suggested solution (or None)
                - error: Error message if something went wrong (or None)
        """
        response = {
            'specialist_name': None,
            'specialist_exists': False,
            'combat_maneuvers_applied': [],
            'evolution_triggered': False,
            'suggested_solution': None,
            'error': None
        }
        
        try:
            # Step 1: Identify library from traceback
            library_name = TracebackAnalyzer.extract_library_name(traceback_str)
            
            if not library_name:
                logger.warning(f"Could not extract library name from traceback:\n{traceback_str}")
                response['error'] = "Could not identify library from traceback"
                return response
            
            response['specialist_name'] = library_name
            logger.info(f"Identified library: {library_name}")
            
            # Step 2: Check if specialist exists
            specialist_exists = AgentFactory._check_specialist_exists(library_name)
            response['specialist_exists'] = specialist_exists
            
            # Step 3: Create specialist if needed
            if not specialist_exists:
                logger.info(f"Creating new specialist for {library_name}")
                created = AgentFactory._create_specialist(
                    library_name,
                    str(exception),
                    traceback_str
                )
                if not created:
                    response['error'] = "Failed to create specialist"
                    return response
            
            # Step 4: Load specialist
            specialist = AgentFactory._load_specialist(library_name)
            if not specialist:
                response['error'] = "Failed to load specialist"
                return response
            
            # Step 5: Apply specialist knowledge
            solution, applied_maneuvers = AgentFactory._apply_specialist(specialist, str(exception))
            response['suggested_solution'] = solution
            response['combat_maneuvers_applied'] = applied_maneuvers
            
            # Step 6: Evolve if needed (solution not found or error persists)
            if not solution:
                logger.info(f"No solution found, evolving specialist for {library_name}")
                evolved = AgentFactory._evolve_specialist(
                    library_name,
                    specialist,
                    str(exception),
                    traceback_str
                )
                response['evolution_triggered'] = evolved
            
            # Optional: log to Neural Link graph
            try:
                from src.neural_link.graph.manager import GraphManager
                gm = GraphManager.from_env()
                if gm.verify_connectivity():
                    gm.execute_write(
                        "MERGE (e:Error {id: $id}) "
                        "SET e.error_type = $error_type, e.message = $message, "
                        "    e.library = $library, e.frequency = coalesce(e.frequency, 0) + 1, "
                        "    e.resolved = $resolved",
                        {
                            "id": f"err_{library_name}_{abs(hash(str(exception))) % 10**8}",
                            "error_type": type(exception).__name__,
                            "message": str(exception)[:500],
                            "library": library_name or "",
                            "resolved": solution is not None,
                        },
                    )
            except (ImportError, Exception):
                pass  # Neural Link not available - system continues normally

            return response

        except Exception as e:
            logger.error(f"Error in handle_exception: {e}", exc_info=True)
            response['error'] = f"Internal error: {str(e)}"
            return response
    
    @staticmethod
    def _check_specialist_exists(library_name: str) -> bool:
        """
        Check if a specialist exists for the given library.
        
        Args:
            library_name: The normalized library name
            
        Returns:
            True if specialist exists, False otherwise
        """
        exists = SpecManager.spec_exists(library_name)
        logger.debug(f"Specialist exists for {library_name}: {exists}")
        return exists
    
    @staticmethod
    def _create_specialist(
        library_name: str,
        error_message: str,
        traceback_str: str
    ) -> bool:
        """
        Create a new specialist via Groq API.
        
        Args:
            library_name: The normalized library name
            error_message: The error message that triggered creation
            traceback_str: The full exception traceback
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate spec content
            spec_content = SpecGenerator.generate_specialist_spec(
                library_name,
                error_message,
                traceback_str
            )
            
            if not spec_content:
                logger.error(f"Failed to generate spec for {library_name}")
                return False
            
            # Save to disk
            saved = SpecManager.save_spec(library_name, spec_content)
            if saved:
                logger.info(f"Created specialist for {library_name} at src/agents/specs/{library_name}.md")
            else:
                logger.error(f"Failed to save spec for {library_name}")
            
            return saved
            
        except Exception as e:
            logger.error(f"Error creating specialist for {library_name}: {e}", exc_info=True)
            return False
    
    @staticmethod
    def _load_specialist(library_name: str) -> Optional[Dict[str, Any]]:
        """
        Load and parse a specialist spec.
        
        Args:
            library_name: The normalized library name
            
        Returns:
            The parsed specialist dict, or None if failed
        """
        try:
            specialist = SpecManager.load_spec(library_name)
            if specialist:
                maneuver_count = len(specialist.get('combat_maneuvers', []))
                logger.info(f"Loaded specialist for {library_name} with {maneuver_count} combat maneuvers")
            else:
                logger.warning(f"Failed to load specialist for {library_name}")
            return specialist
        except Exception as e:
            logger.error(f"Error loading specialist for {library_name}: {e}", exc_info=True)
            return None
    
    @staticmethod
    def _apply_specialist(
        specialist: Dict[str, Any],
        error_message: str
    ) -> tuple[Optional[str], list[str]]:
        """
        Apply specialist knowledge to the error.
        
        Args:
            specialist: The parsed specialist dict
            error_message: The error message to match against
            
        Returns:
            A tuple of (suggested_solution, list_of_applied_maneuver_titles)
        """
        try:
            combat_maneuvers = specialist.get('combat_maneuvers', [])
            applied_maneuvers = []
            
            # Try to match error message against combat maneuver signatures
            for maneuver in combat_maneuvers:
                error_sig = maneuver.get('error_signature', '')
                if error_sig and error_sig.lower() in error_message.lower():
                    solution = maneuver.get('solution_code', '')
                    title = maneuver.get('title', 'Untitled')
                    applied_maneuvers.append(title)
                    logger.info(f"Applied combat maneuver: {title}")
                    return solution, applied_maneuvers
            
            logger.debug("No matching combat maneuver found")
            return None, []
            
        except Exception as e:
            logger.error(f"Error applying specialist: {e}", exc_info=True)
            return None, []
    
    @staticmethod
    def _evolve_specialist(
        library_name: str,
        specialist: Dict[str, Any],
        error_message: str,
        traceback_str: str
    ) -> bool:
        """
        Evolve a specialist with a new combat maneuver.
        
        Args:
            library_name: The normalized library name
            specialist: The current specialist dict
            error_message: The error message that triggered evolution
            traceback_str: The full exception traceback
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate new combat maneuver
            existing_maneuvers = specialist.get('combat_maneuvers', [])
            new_maneuver = SpecGenerator.generate_combat_maneuver(
                library_name,
                error_message,
                traceback_str,
                existing_maneuvers
            )
            
            if not new_maneuver:
                logger.error(f"Failed to generate combat maneuver for {library_name}")
                return False
            
            # Create evolution history entry
            evolution_entry = {
                'timestamp': new_maneuver.get('learned_on', ''),
                'error_type': error_message[:50],  # Truncate for brevity
                'solution_summary': new_maneuver.get('error_signature', 'New maneuver')[:100]
            }
            
            # Update spec file
            updated = SpecManager.update_spec(library_name, new_maneuver, evolution_entry)
            if updated:
                logger.info(f"Evolved specialist for {library_name}: {evolution_entry['solution_summary']}")
            else:
                logger.error(f"Failed to update spec for {library_name}")
            
            return updated
            
        except Exception as e:
            logger.error(f"Error evolving specialist for {library_name}: {e}", exc_info=True)
            return False
