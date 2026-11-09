from pathlib import Path
from typing import Dict, Any
from ..config import config

class PromptManager:
    """Loads and formats markdown prompt templates from the prompts directory."""

    def __init__(self, prompt_dir: Path = None):
        self.prompt_dir = prompt_dir or config.prompt_dir

    def load_prompt(self, filename: str) -> str:
        """Load raw prompt template text."""
        path = self.prompt_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Prompt template file not found: {path}")
        return path.read_text(encoding="utf-8")

    def render(self, filename: str, variables: Dict[str, Any]) -> str:
        """Render prompt template by substituting {PLACEHOLDER} tokens."""
        template = self.load_prompt(filename)
        rendered = template
        for key, val in variables.items():
            placeholder = f"{{{key.upper()}}}"
            # Format value if list or dict
            if isinstance(val, (list, tuple)):
                if all(isinstance(x, str) for x in val):
                    str_val = "\n".join(f"- {x}" for x in val)
                else:
                    import json
                    str_val = json.dumps(val, indent=2)
            elif val is None:
                str_val = "None specified"
            else:
                str_val = str(val)
            rendered = rendered.replace(placeholder, str_val)
        return rendered

prompt_manager = PromptManager()
