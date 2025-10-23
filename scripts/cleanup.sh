#!/usr/bin/env bash
# filepath: /workspaces/LLM_research/scripts/cleanup.sh
# Güvenli proje temizleyici
set -euo pipefail

DRY_RUN=true
FORCE=false

for arg in "$@"; do
  case "$arg" in
    --yes|--force|-y) DRY_RUN=false; FORCE=true;;
    --no-dry-run) DRY_RUN=false;;
    --dry-run) DRY_RUN=true;;
    -h|--help) printf "Kullanım: %s [--dry-run] [--yes|--force]\n" "$0"; exit 0;;
  esac
done

TARGETS=(
  "dump.rdb"
  "env.txt"
  "__pycache__"
  ".pytest_cache"
  "logs"
)

PYCS=$(find . -type f -name "*.pyc" 2>/dev/null || true)

printf "=== Temizlik özet (dry-run=%s) ===\n" "$DRY_RUN"
for t in "${TARGETS[@]}"; do
  if [ -e "$t" ]; then
    printf "Bulundu: %s\n" "$t"
  else
    printf "Yok: %s\n" "$t"
  fi
done

if [ -n "$PYCS" ]; then
  printf "Bulunan .pyc dosyaları (örnek):\n"
  printf "%s\n" "$PYCS" | head -n 20
else
  printf "Herhangi bir .pyc dosyası bulunamadı.\n"
fi

if $DRY_RUN; then
  printf "\nDry-run: yukarıdaki öğeler silinmeyecek. Gerçek silme için --yes veya --no-dry-run ile çalıştırın.\n"
  exit 0
fi

# Non-interactive ortam kontrolü
if [ "$FORCE" = false ] && [ ! -t 0 ]; then
  printf "Non-interactive ortamda onay bekleniyor; --yes ile çalıştırın.\n" >&2
  exit 1
fi

if [ "$FORCE" = false ]; then
  read -r -p "Silme işlemini onaylıyor musunuz? (y/N): " CONF
  if [[ ! "$CONF" =~ ^[Yy]$ ]]; then
    printf "İptal edildi.\n"
    exit 0
  fi
fi

printf "Siliniyor...\n"
for t in "${TARGETS[@]}"; do
  if [ -e "$t" ]; then
    rm -rf "$t" && printf "Silindi: %s\n" "$t" || printf "Silme hatası: %s\n" "$t"
  fi
done

if [ -n "$PYCS" ]; then
  find . -type f -name "*.pyc" -delete || true
  printf ".pyc dosyaları silindi.\n"
fi

printf "Temizlik tamamlandı.\n"
