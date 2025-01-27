# painter.py

from typing import List

class TextPainter:
    def __init__(self, utilities, base_color='GREEN'):
        self.utils = utilities
        self._base_color = self.utils.get_base_color(base_color)
        self.active_patterns: List[str] = []
        
        # Get validated pattern maps
        self.by_name = self.utils.by_name
        self.start_map = self.utils.start_map
        self.end_map = self.utils.end_map

    def process_chunk(self, text: str) -> str:
        """Process a chunk of text and apply ANSI styling."""
        if not text:
            return ""
            
        out, i = [], 0
        
        if not self.active_patterns:
            out.append(self.utils.get_format('ITALIC_OFF') + 
                      self.utils.get_format('BOLD_OFF') + 
                      self._base_color)
            
        while i < len(text):
            ch = text[i]
            
            if i == 0 or text[i-1].isspace():
                out.append(self.utils.get_style(self.active_patterns, self._base_color))
                
            if self.active_patterns and ch in self.end_map:
                if ch == self.by_name[self.active_patterns[-1]].end:
                    pat = self.by_name[self.active_patterns[-1]]
                    if not pat.remove_delimiters:
                        out.append(self.utils.get_style(self.active_patterns, self._base_color) + ch)
                    self.active_patterns.pop()
                    out.append(self.utils.get_style(self.active_patterns, self._base_color))
                    i += 1
                    continue
                    
            if ch in self.start_map:
                new_pat = self.start_map[ch]
                self.active_patterns.append(new_pat.name)
                out.append(self.utils.get_style(self.active_patterns, self._base_color))
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