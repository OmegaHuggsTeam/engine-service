"""
Grimoire Manager - Gerencia persistência de skills no grimório.

Este módulo implementa o sistema de persistência que salva e carrega skills
do arquivo selenium.md.
"""

import os
import re
from datetime import datetime
from typing import Dict


class GrimoireManager:
    """Gerencia persistência de skills no grimório."""
    
    GRIMOIRE_PATH = "src/agents/specs/selenium.md"
    CUSTOM_SKILLS_SECTION = "## Custom Skills Learned"
    
    @staticmethod
    def save_skill(
        skill_name: str,
        skill_code: str,
        problem_description: str,
        original_context: str
    ) -> bool:
        """
        Salva uma skill no grimório.
        
        Args:
            skill_name: Nome da skill
            skill_code: Código Python da skill
            problem_description: Descrição do problema resolvido
            original_context: Contexto original do erro
            
        Returns:
            True se bem-sucedido, False caso contrário
        """
        try:
            # Ler arquivo existente
            if os.path.exists(GrimoireManager.GRIMOIRE_PATH):
                with open(GrimoireManager.GRIMOIRE_PATH, 'r', encoding='utf-8') as f:
                    content = f.read()
            else:
                # Criar estrutura básica
                content = "# Specialist: selenium\n\n"
            
            # Verificar se seção existe
            if GrimoireManager.CUSTOM_SKILLS_SECTION not in content:
                content += f"\n{GrimoireManager.CUSTOM_SKILLS_SECTION}\n\n"
            
            # Criar entrada da skill
            timestamp = datetime.now().isoformat()
            skill_entry = f"""
### Skill: {skill_name}
- **Problem Solved**: {problem_description}
- **Learned On**: {timestamp}
- **Original Context**: {original_context[:200]}...
- **Code**:
```python
{skill_code}
```

"""
            
            # Adicionar ao final da seção
            parts = content.split(GrimoireManager.CUSTOM_SKILLS_SECTION)
            if len(parts) >= 2:
                content = parts[0] + GrimoireManager.CUSTOM_SKILLS_SECTION + parts[1] + skill_entry
            else:
                content += skill_entry
            
            # Salvar arquivo
            os.makedirs(os.path.dirname(GrimoireManager.GRIMOIRE_PATH), exist_ok=True)
            with open(GrimoireManager.GRIMOIRE_PATH, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
        
        except Exception as e:
            # Log será feito pelo chamador
            return False
    
    @staticmethod
    def load_skills() -> Dict[str, str]:
        """
        Carrega skills do grimório.
        
        Returns:
            Dict[skill_name, skill_code]
        """
        skills = {}
        
        try:
            if not os.path.exists(GrimoireManager.GRIMOIRE_PATH):
                return skills
            
            with open(GrimoireManager.GRIMOIRE_PATH, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Verificar se seção existe
            if GrimoireManager.CUSTOM_SKILLS_SECTION not in content:
                return skills
            
            # Extrair seção de skills
            parts = content.split(GrimoireManager.CUSTOM_SKILLS_SECTION)
            if len(parts) < 2:
                return skills
            
            section = parts[1]
            
            # Parsear skills
            skill_pattern = r'### Skill: (skill_\w+).*?```python\n(.*?)```'
            matches = re.findall(skill_pattern, section, re.DOTALL)
            
            for skill_name, skill_code in matches:
                skills[skill_name] = skill_code.strip()
            
            return skills
        
        except Exception as e:
            # Log será feito pelo chamador
            return skills
