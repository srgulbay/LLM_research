# Basit dönüşüm scripti: tüm _new.html dosyalarında sık kullanılan sınıfları dark: alternatifleriyle günceller.
# Çalıştırmadan önce commit yapın veya dosyaları yedekleyin. Script .bak yedekleri oluşturur.

import re
from pathlib import Path

ROOT = Path('/workspaces/LLM_research/templates')
patterns = {
    r'\bbg-white\b': 'bg-white dark:bg-slate-800',
    r'\btext-slate-900\b': 'text-slate-900 dark:text-white',
    r'\btext-slate-800\b': 'text-slate-800 dark:text-slate-200',
    r'\btext-slate-700\b': 'text-slate-700 dark:text-slate-200',
    r'\btext-slate-600\b': 'text-slate-600 dark:text-slate-400',
    r'\btext-slate-500\b': 'text-slate-500 dark:text-slate-400',
    r'\bborder-slate-200\b': 'border-slate-200 dark:border-slate-700',
    r'\bbg-slate-50\b': 'bg-slate-50 dark:bg-slate-800',
    r'\bbg-slate-100\b': 'bg-slate-100 dark:bg-slate-700',
    r'\bbg-green-50\b': 'bg-green-50 dark:bg-green-900/20',
    r'\bbg-blue-50\b': 'bg-blue-50 dark:bg-blue-900/20',
}

files = list(ROOT.rglob('*_new.html')) + list((ROOT / 'admin').rglob('*_new.html')) if (ROOT / 'admin').exists() else list(ROOT.rglob('*_new.html'))

for f in files:
    text = f.read_text(encoding='utf-8')
    orig = text
    for pat, repl in patterns.items():
        text = re.sub(pat, repl, text)
    if text != orig:
        bak = f.with_suffix(f.suffix + '.bak')
        bak.write_text(orig, encoding='utf-8')
        f.write_text(text, encoding='utf-8')
        print(f'Updated: {f} (backup: {bak})')
    else:
        print(f'No changes: {f}')

print('Tamamlandı. .bak dosyalarını inceleyin ve değişiklikleri doğrulayın.')