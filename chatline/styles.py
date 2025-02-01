# styles.py

import re
from typing import List, Optional, Dict
from dataclasses import dataclass
from rich.style import Style

ANSI_REGEX = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
FMT = lambda x: f'\033[{x}m'
FORMATS = {
    'RESET': FMT('0'),
    'ITALIC_ON': FMT('3'),
    'ITALIC_OFF': FMT('23'),
    'BOLD_ON': FMT('1'),
    'BOLD_OFF': FMT('22')
}
COLORS = {
    'GREEN': {'ansi': '\033[38;5;47m', 'rich': 'green3'},
    'PINK':  {'ansi': '\033[38;5;212m','rich': 'pink1'},
    'BLUE':  {'ansi': '\033[38;5;75m', 'rich': 'blue1'}
}
STYLE_PATTERNS = {
    'quotes':   {'start': '"', 'end': '"', 'color': 'PINK'},
    'brackets': {'start': '[', 'end': ']', 'color': 'BLUE'},
    'emphasis': {'start': '_', 'end': '_', 'color': None, 'styles': ['ITALIC'], 'remove_delimiters': True},
    'strong':   {'start': '*', 'end': '*', 'color': None, 'styles': ['BOLD'],   'remove_delimiters': True}
}
STYLE_PATTERNS.update({
    k:{**v,'styles':[],'remove_delimiters':False}
    for k,v in list(STYLE_PATTERNS.items())[:2]
})

@dataclass
class Pattern:
    name: str
    start: str
    end: str
    color: Optional[str]
    styles: List[str] = None
    remove_delimiters: bool = False

class Styles:
    def __init__(self):
        self.by_name,self.start_map,self.end_map={}, {}, {}
        used=set()
        for name,cfg in STYLE_PATTERNS.items():
            pat=Pattern(name=name,**cfg)
            if pat.start in used or pat.end in used:
                raise ValueError(f"Duplicate delimiter in '{pat.name}'")
            used.update([pat.start, pat.end])
            self.by_name[name]=self.start_map[pat.start]=self.end_map[pat.end]=pat
        self.rich_styles={n:Style(color=c['rich']) for n,c in COLORS.items()}

    def get_format(self, name:str) -> str: return FORMATS.get(name,'')
    def get_color(self, name:str) -> str: return COLORS.get(name,{}).get('ansi','')
    def get_rich_style(self, name:str) -> Style: return self.rich_styles.get(name,Style())
    def get_base_color(self, color_name:str='GREEN')->str: return COLORS.get(color_name,{}).get('ansi','')

    def get_visible_length(self, text:str) -> int:
        text=ANSI_REGEX.sub('', text)
        for c in ['─','│','╭','╮','╯','╰']: text=text.replace(c,'')
        return len(text)

    def get_style(self, active_patterns:List[str], base_color:str)->str:
        style=[base_color]
        for n in active_patterns:
            pat=self.by_name[n]
            if pat.color: style[0]=COLORS[pat.color]['ansi']
            style.extend(FORMATS[f'{s}_ON'] for s in (pat.styles or []))
        return ''.join(style)

    def split_text(self, text:str, width:Optional[int]=None)->List[str]:
        if width is None: width=80
        has_borders='─' in text or '│' in text
        if has_borders: width=max(width-4,20)
        lines,curr_line,curr_len=[],[],0
        for w in text.split():
            if has_borders and w.strip('─│╭╮╯╰')=='':
                lines.append(w)
                continue
            if len(w)>width:
                if curr_line: lines.append(' '.join(curr_line))
                lines.extend(w[i:i+width] for i in range(0,len(w),width))
                curr_line,curr_len=[],0
                continue
            wl=len(w)+(1 if curr_len else 0)
            if curr_len+wl<=width:
                curr_line.append(w)
                curr_len+=wl
            else:
                lines.append(' '.join(curr_line))
                curr_line,curr_len=[w],len(w)
        if curr_line: lines.append(' '.join(curr_line))
        return lines

    def split_into_styled_words(self, text:str)->List[dict]:
        words=[]; curr={'word':[],'styled':[],'patterns':[]}
        for i,ch in enumerate(text):
            if ch in self.start_map:
                pat=self.start_map[ch]
                curr['patterns'].append(pat.name)
                if not pat.remove_delimiters:
                    curr['word'].append(ch); curr['styled'].append(ch)
            elif curr['patterns'] and ch in self.end_map:
                pat=self.by_name[curr['patterns'][-1]]
                if ch==pat.end:
                    if not pat.remove_delimiters:
                        curr['word'].append(ch); curr['styled'].append(ch)
                    curr['patterns'].pop()
            elif ch.isspace():
                if curr['word']:
                    words.append({
                        'raw_text':''.join(curr['word']),
                        'styled_text':''.join(curr['styled']),
                        'active_patterns':curr['patterns'].copy()
                    }); curr={'word':[],'styled':[],'patterns':[]}
            else:
                curr['word'].append(ch); curr['styled'].append(ch)
        if curr['word']:
            words.append({
                'raw_text':''.join(curr['word']),
                'styled_text':''.join(curr['styled']),
                'active_patterns':curr['patterns'].copy()
            })
        return words

    def format_styled_lines(self, lines:List[List[dict]], base_color:str)->str:
        res=[]; curr_style=self.get_format('RESET')+base_color
        for line in lines:
            c=[curr_style]
            for w in line:
                s=self.get_style(w['active_patterns'], base_color)
                if s!=curr_style: c.append(s); curr_style=s
                c.append(w['styled_text']+" ")
            f="".join(c).rstrip()
            if f: res.append(f)
        extra=self.get_format('RESET')+base_color
        return "\n".join(res)+(extra if curr_style!=extra else "")
