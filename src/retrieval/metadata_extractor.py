"""
metadata_extractor.py — Ekstrak metadata terstruktur dari teks chunk regulasi.
Dipanggil saat ingest untuk memperkaya setiap node dengan identifier spesifik.
"""

import re
from typing import Dict, Optional


# Pola regulasi Indonesia
_REGULATION_PATTERNS = [
    # "PBI No. 23/6/PBI/2021" atau "PBI 23/6/2021"
    (r'(?:PBI|SEBI)\s*(?:No\.?\s*)?(\d+/\d+(?:/PBI|/SEBI)?(?:/\d{4})?)', 'BI'),
    # "POJK No. 22 Tahun 2023" atau "POJK 22/2023"
    (r'POJK\s*(?:No\.?\s*)?(\d+(?:/\d+)?)\s*(?:Tahun\s*(\d{4}))?', 'OJK'),
    # "Peraturan Bank Indonesia Nomor 23/6/PBI/2021"
    (r'Peraturan Bank Indonesia\s+(?:Nomor\s+)?(\d+/\d+(?:/PBI)?(?:/\d{4})?)', 'BI'),
    # "Peraturan OJK Nomor 22 Tahun 2023"
    (r'Peraturan\s+(?:Otoritas Jasa Keuangan|OJK)\s+(?:Nomor\s+)?(\d+)\s+Tahun\s+(\d{4})', 'OJK'),
]

_PASAL_PATTERN = re.compile(r'\bPasal\s+(\d+)\b', re.IGNORECASE)
_AYAT_PATTERN  = re.compile(r'\b[Aa]yat\s+\(?\s*(\d+|[a-z])\s*\)?', re.IGNORECASE)
_YEAR_PATTERN  = re.compile(r'\b(20\d{2})\b')

# Map nama file ke kode regulasi
_FILENAME_MAP = {
    'PBI_22_23': ('PBI 22/23/PBI/2020', '2020', 'BI'),
    'PBI_23_6':  ('PBI 23/6/PBI/2021',  '2021', 'BI'),
    'POJK_22':   ('POJK 22/2023',        '2023', 'OJK'),
    'PBI2223':   ('PBI 22/23/PBI/2020',  '2020', 'BI'),
    'PBI236':    ('PBI 23/6/PBI/2021',   '2021', 'BI'),
    'POJK22':    ('POJK 22/2023',        '2023', 'OJK'),
}


def _detect_from_filename(filename: str) -> Dict[str, str]:
    """Coba deteksi kode regulasi dari nama file."""
    fn = filename.upper().replace('-', '_').replace(' ', '_')
    for key, (code, year, regulator_type) in _FILENAME_MAP.items():
        if key.replace('_', '') in fn.replace('_', ''):
            return {
                'regulation_code': code,
                'regulation_year': year,
                'regulation_type': regulator_type,
            }
    # Fallback: cari pola PBI/POJK di nama file
    if 'PBI' in fn:
        return {'regulation_code': '', 'regulation_year': '', 'regulation_type': 'BI'}
    if 'POJK' in fn:
        return {'regulation_code': '', 'regulation_year': '', 'regulation_type': 'OJK'}
    return {}


def extract_regulation_metadata(text: str, filename: str = '') -> Dict[str, str]:
    """
    Ekstrak metadata terstruktur dari konten teks chunk.

    Returns dict dengan keys:
        regulation_code    : "PBI 23/6/PBI/2021"
        regulation_number  : "23/6/2021"
        regulation_year    : "2021"
        regulation_type    : "BI" | "OJK"
        pasal_number       : "160"  (pasal pertama yang terdeteksi di heading)
        ayat_number        : "2"    (ayat pertama yang terdeteksi)
        section_heading    : "Pasal 160 Ayat 2"
    """
    result: Dict[str, str] = {}

    # --- Kode regulasi dari nama file (lebih reliable) ---
    if filename:
        file_meta = _detect_from_filename(filename)
        result.update(file_meta)

    # --- Kode regulasi dari teks ---
    if not result.get('regulation_code'):
        for pattern, reg_type in _REGULATION_PATTERNS:
            m = re.search(pattern, text)
            if m:
                code = m.group(0).strip()
                result['regulation_code'] = code
                result['regulation_type'] = reg_type
                # Cari tahun
                year_m = _YEAR_PATTERN.search(code)
                if not year_m:
                    year_m = _YEAR_PATTERN.search(text)
                result['regulation_year'] = year_m.group(1) if year_m else ''
                # Nomor saja (tanpa prefix PBI/POJK)
                result['regulation_number'] = m.group(1) if m.lastindex and m.lastindex >= 1 else ''
                break

    # --- Nomor pasal (ambil dari baris pertama / heading) ---
    lines = text.split('\n')
    heading_text = ' '.join(lines[:5])  # 5 baris pertama sebagai kandidat heading
    pasal_m = _PASAL_PATTERN.search(heading_text)
    if not pasal_m:
        pasal_m = _PASAL_PATTERN.search(text)
    if pasal_m:
        result['pasal_number'] = pasal_m.group(1)

    # --- Nomor ayat ---
    ayat_m = _AYAT_PATTERN.search(heading_text)
    if not ayat_m:
        ayat_m = _AYAT_PATTERN.search(text)
    if ayat_m:
        result['ayat_number'] = ayat_m.group(1)

    # --- Section heading gabungan ---
    heading_parts = []
    if result.get('pasal_number'):
        heading_parts.append(f"Pasal {result['pasal_number']}")
    if result.get('ayat_number'):
        heading_parts.append(f"Ayat {result['ayat_number']}")
    result['section_heading'] = ' '.join(heading_parts)

    return result
