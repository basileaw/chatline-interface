# painter.py
from dataclasses import dataclass
from typing import Optional, List, Dict
import json

# ANSI Format Codes (add more as needed)
FORMATS = {
    'RESET': '\033[0m',
    'ITALIC_ON': '\033[3m',
    'ITALIC_OFF': '\033[23m'
}

# Color Palette - Using xterm-256 color codes (add more as needed)
COLORS = {
    'GREEN': '\033[38;5;47m',     # Base text color
    'PINK': '\033[38;5;212m',     # Dialogue
    'BLUE': '\033[38;5;75m'       # Observations
}

# Default Pattern Styles (modify or add new patterns as needed)
DEFAULT_PATTERNS = [
    {
        'name': 'quotes',
        'start': '"',
        'end': '"',
        'color': COLORS['PINK'],
        'italic': False,
        'remove_delimiters': False  # Keep quotes visible
    },
    {
        'name': 'brackets',
        'start': '[',
        'end': ']',
        'color': COLORS['BLUE'],
        'italic': False,
        'remove_delimiters': False  # Keep brackets visible
    },
    {
        'name': 'emphasis',
        'start': '_',
        'end': '_',
        'color': None,
        'italic': True,
        'remove_delimiters': True   # Hide underscores
    }
]

@dataclass
class Pattern:
    """Text pattern with associated styling."""
    name: str
    start: str
    end: str
    color: Optional[str]
    italic: bool
    remove_delimiters: bool

class Paint:
    """Processes text streams and applies pattern-based ANSI styling."""
    
    def __init__(self, patterns: List[Dict] = None, base_color: str = COLORS['GREEN']):
        self.base_color = base_color
        self.active_patterns = []
        self.patterns = [Pattern(**p) for p in (patterns or DEFAULT_PATTERNS)]
        
        # Validate pattern characters are unique
        used_chars = set()
        for p in self.patterns:
            if p.start in used_chars or p.end in used_chars:
                raise ValueError(f"Pattern '{p.name}' uses a character that's already in use")
            used_chars.update([p.start, p.end])
        
        # Create lookup maps for efficient pattern matching
        self.by_name = {p.name: p for p in self.patterns}
        self.start_map = {p.start: p for p in self.patterns}
        self.end_map = {p.end: p for p in self.patterns}

    def get_style(self) -> str:
        """Get current ANSI style based on active patterns."""
        color = self.base_color
        italic = False
        for name in self.active_patterns:
            p = self.by_name[name]
            if p.color: color = p.color
            if p.italic: italic = True
        return (FORMATS['ITALIC_ON'] if italic else FORMATS['ITALIC_OFF']) + color

    def process_chunk(self, chunk: str) -> None:
        """Process a chunk of text, applying patterns and styles in real-time."""
        if not chunk: return
        output = []
        i = 0
        
        if not self.active_patterns:
            output.append(FORMATS['ITALIC_OFF'] + self.base_color)
        
        while i < len(chunk):
            ch = chunk[i]
            
            if self.active_patterns and ch in self.end_map and ch == self.by_name[self.active_patterns[-1]].end:
                current_pat = self.by_name[self.active_patterns[-1]]
                if not current_pat.remove_delimiters:
                    output.append(self.get_style() + ch)
                self.active_patterns.pop()
                output.append(self.get_style())
                i += 1
                continue
            
            if ch in self.start_map:
                new_pat = self.start_map[ch]
                self.active_patterns.append(new_pat.name)
                output.append(self.get_style())
                if not new_pat.remove_delimiters:
                    output.append(ch)
                i += 1
                continue
            
            output.append(ch)
            i += 1
        
        print("".join(output), end='', flush=True)


def run_demo():
    """Demo using the generator from the imported module."""
    from generator import generate_stream
    painter = Paint()
    
    messages = [
        {
            "role": "system",
            "content": 'Write a succinct paragraph using multiple styles:\n- "quotes" for dialogue\n- [brackets] for observations\n- _underscores_ for emphasis'
        },
        {
            "role": "user",
            "content": "Write a mystery scene using all text styles."
        }
    ]
    
    for output in generate_stream(messages):
        try:
            data = json.loads(output.replace('data: ', '').strip())
            if data == '[DONE]':
                print(FORMATS['RESET'])
                break
            if data != '[ERROR]':
                painter.process_chunk(data['choices'][0]['delta']['content'])
        except json.JSONDecodeError:
            continue
    print('\n')

if __name__ == "__main__":
    run_demo()