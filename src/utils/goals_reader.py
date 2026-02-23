try:
    import mistune
except ImportError:
    mistune = None
from pathlib import Path

from ..config import settings
from ..exceptions import FileProcessingException
from ..config.logging_config import get_logger

logger = get_logger(__name__)


def _load_goals_file() -> str:
    """Load the Business_Goals.md content.

    The path is resolved relative to the project root. If the file cannot be found,
    a ``FileProcessingException`` is raised so callers can handle the error.
    """
    # Default location is the repository root
    default_path = Path(settings.BASE_DIR) / 'Business_Goals.md'
    path = Path(settings.BASE_DIR) / settings.COMPANY_HANDBOOK_PATH if getattr(settings, 'COMPANY_HANDBOOK_PATH', None) else default_path
    if not path.is_file():
        path = default_path
    try:
        return path.read_text(encoding='utf-8')
    except Exception as e:
        raise FileProcessingException(f"Failed to read Business_Goals.md at {path}: {e}")


def extract_section(markdown: str, heading: str) -> str:
    """Return the content under a level‑2 heading.

    Parameters
    ----------
    markdown: str
        Full markdown text.
    heading: str
        The heading title to extract (case‑insensitive).
    """
    if mistune:
        try:
            # Try modern mistune API first
            parser = mistune.create_markdown(renderer=mistune.AstRenderer())
            ast = parser(markdown)
            collecting = False
            lines = []
            for token in ast:
                if token['type'] == 'heading' and token['level'] == 2:
                    # Compare heading text without markdown formatting
                    current = token['children'][0]['text'].strip().lower()
                    collecting = current == heading.lower()
                    continue
                if collecting:
                    if token['type'] == 'heading' and token['level'] <= 2:
                        break
                    if token['type'] == 'paragraph':
                        lines.append(token['children'][0]['text'])
                    elif token['type'] == 'list':
                        for item in token['children']:
                            lines.append(f"- {item['children'][0]['text']}")
            return "\n".join(lines).strip()
        except (AttributeError, TypeError):
            # Fall back to simple parser if mistune API is incompatible
            logger.warning("Mistune API incompatible, falling back to simple parser")
            pass

    # Simple fallback: split by lines and look for headings
    lines = []
    collecting = False
    for raw_line in markdown.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith('##'):
            header = stripped.lstrip('#').strip().lower()
            collecting = (header == heading.lower())
            continue
        if collecting:
            if stripped.startswith('##'):
                break
            lines.append(stripped)
    return "\n".join(lines).strip()


def get_metrics() -> str:
    """Extract the ``## Metrics`` section from Business_Goals.md."""
    return extract_section(_load_goals_file(), "Metrics")


def get_rules() -> str:
    """Extract the ``## Rules`` section from Business_Goals.md."""
    return extract_section(_load_goals_file(), "Rules")
