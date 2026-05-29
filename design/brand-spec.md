# Daily AI News Desk brand spec

Source basis: user-provided text references A and B. No external screenshot, CSS,
PDF, or URL was present in the project folder, so the system below is extracted
from the written direction: public editorial news service, off-white reading
surface, sharp black typography, restrained coral/red accent, teal as a
secondary source/status signal, and no purple admin/neumorphic treatment.

## Tokens

```css
:root {
  --bg:      oklch(98% 0.006 88);
  --surface: oklch(100% 0.002 88);
  --fg:      oklch(17% 0.018 70);
  --muted:   oklch(46% 0.014 72);
  --border:  oklch(89% 0.008 88);
  --accent:  oklch(58% 0.145 32);
}
```

## Type

- Display: "Apple SD Gothic Neo", "Pretendard", "Noto Sans KR", "Segoe UI", system-ui, sans-serif
- Body: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif
- Mono: "SFMono-Regular", "JetBrains Mono", ui-monospace, Menlo, monospace

## Layout posture

- Main reading column owns the page; right rail is utility/navigation, never the
  visual anchor.
- Use fine borders and whitespace rather than soft shadows or neumorphic blocks.
- Coral/red appears only for editorial emphasis, selected state, and primary CTA.
- Teal appears as a secondary signal for source chips, publish dots, and status.
- Cards stay flat and un-nested; dense information is grouped by label, divider,
  and typographic hierarchy instead of box-in-box chrome.
