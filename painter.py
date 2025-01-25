# painter.py

from dataclasses import dataclass
from typing import Optional, List, Dict

# Extended ANSI codes + colors
FORMATS = {
    'RESET': '\033[0m',
    'ITALIC_ON': '\033[3m',
    'ITALIC_OFF': '\033[23m',
    'BOLD_ON': '\033[1m',
    'BOLD_OFF': '\033[22m'
}

COLORS = {
    'GREEN': '\033[38;5;47m',
    'PINK': '\033[38;5;212m',
    'BLUE': '\033[38;5;75m'
}

@dataclass
class Pattern:
    name: str
    start: str
    end: str
    color: Optional[str]
    italic: bool
    bold: bool
    remove_delimiters: bool

class TextPainter:
    def __init__(self, patterns: List[Dict] = None, base_color=COLORS['GREEN']):
        default_patterns = [
            {'name': 'quotes', 'start': '"', 'end': '"', 'color': COLORS['PINK'], 
             'italic': False, 'bold': False, 'remove_delimiters': False},
            {'name': 'brackets', 'start': '[', 'end': ']', 'color': COLORS['BLUE'], 
             'italic': False, 'bold': False, 'remove_delimiters': False},
            {'name': 'emphasis', 'start': '_', 'end': '_', 'color': None, 
             'italic': True, 'bold': False, 'remove_delimiters': True},
            {'name': 'strong', 'start': '*', 'end': '*', 'color': None, 
             'italic': False, 'bold': True, 'remove_delimiters': True}
        ]
        self.patterns = [Pattern(**p) for p in (patterns or default_patterns)]
        self.base_color = base_color
        self.active_patterns: List[str] = []

        # Validate patterns
        used = set()
        for p in self.patterns:
            if p.start in used or p.end in used:
                raise ValueError(f"Duplicate delimiter in '{p.name}'")
            used.update([p.start, p.end])

        self.by_name = {p.name: p for p in self.patterns}
        self.start_map = {p.start: p for p in self.patterns}
        self.end_map = {p.end: p for p in self.patterns}

    def get_style(self) -> str:
        """Get current ANSI style based on active patterns."""
        color = self.base_color
        italic = False
        bold = False
        
        for name in self.active_patterns:
            pat = self.by_name[name]
            if pat.color: color = pat.color
            if pat.italic: italic = True
            if pat.bold: bold = True
            
        style = color
        if italic: style += FORMATS['ITALIC_ON']
        if bold: style += FORMATS['BOLD_ON']
        return style

    def process_chunk(self, text: str) -> str:
        """Process a chunk of text and apply ANSI styling."""
        if not text: return ""
        out, i = [], 0
        
        if not self.active_patterns:
            out.append(FORMATS['ITALIC_OFF'] + FORMATS['BOLD_OFF'] + self.base_color)
            
        while i < len(text):
            ch = text[i]
            if i == 0 or text[i-1].isspace():
                out.append(self.get_style())
                
            if self.active_patterns and ch in self.end_map:
                if ch == self.by_name[self.active_patterns[-1]].end:
                    pat = self.by_name[self.active_patterns[-1]]
                    if not pat.remove_delimiters: 
                        out.append(self.get_style()+ch)
                    self.active_patterns.pop()
                    out.append(self.get_style())
                    i += 1
                    continue
                    
            if ch in self.start_map:
                new_pat = self.start_map[ch]
                self.active_patterns.append(new_pat.name)
                out.append(self.get_style())
                if not new_pat.remove_delimiters: 
                    out.append(ch)
                i += 1
                continue
                
            out.append(ch)
            i += 1
            
        return "".join(out)

    def reset(self) -> None:
        """Reset all active patterns."""
        self.active_patterns.clear()