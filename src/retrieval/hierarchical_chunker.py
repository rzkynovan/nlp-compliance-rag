"""
hierarchical_chunker.py — Hierarchical chunking dokumen regulasi Indonesia.

Implementasi Subbab 3.3.1 & 3.4.3 proposal: dokumen regulasi dipotong mengikuti
struktur Bab → Bagian → (Paragraf) → Pasal → Ayat → Huruf dan setiap chunk
membawa metadata hierarki lengkap.

Aturan pemotongan:
  - Unit dasar chunk = satu Pasal (integritas pasal-ayat dijaga).
  - Pasal yang lebih panjang dari `max_chars` dipecah per kelompok Ayat yang
    berurutan; Ayat yang masih terlalu panjang dipecah per kelompok Huruf.
  - Setiap chunk diawali breadcrumb hierarki ("PBI 23/6/PBI/2021 | BAB II ... |
    Pasal 2 ayat (1)") agar konteks posisi ikut ter-embed dan ter-index BM25.
  - Bagian PENJELASAN diberi metadata section="penjelasan"; entri "Cukup jelas."
    dibuang karena tidak informatif.

Masukan berupa teks dokumen utuh (hasil LlamaParse markdown maupun ekstraksi
teks biasa). Penanda markdown (#, *, _) di awal baris diabaikan.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ── Pola penanda struktur (dicocokkan terhadap baris yang sudah dinormalisasi) ──
_BAB_RE       = re.compile(r'^BAB\s+([IVXLC]+)\b\.?\s*(.*)$')
_BAGIAN_RE    = re.compile(r'^Bagian\s+(Ke[a-z]+)\b\.?\s*(.*)$')
_PARAGRAF_RE  = re.compile(r'^Paragraf\s+(\d+)\b\.?\s*(.*)$')
_PASAL_RE     = re.compile(r'^Pasal\s+(\d+)([A-Z]?)\s*$')
_AYAT_RE      = re.compile(r'^(?:Ayat\s*)?\((\d+[a-z]?)\)\s*(.*)$')
_HURUF_RE     = re.compile(r'^(?:Huruf\s+([a-z]{1,2})|([a-z]{1,2})\.)(?:\s+(.*))?$')
_PENJELASAN_RE = re.compile(r'^PENJELASAN\b')
_PENUTUP_RE   = re.compile(r'^Ditetapkan\s+di\b', re.IGNORECASE)
_PAGE_NUM_RE  = re.compile(r'^-\s*\d+\s*-$')
_MD_PREFIX_RE = re.compile(r'^[#>*_\s]+')
_MD_SUFFIX_RE = re.compile(r'[*_\s]+$')
_CUKUP_JELAS_RE = re.compile(r'^cukup jelas\.?$', re.IGNORECASE)


@dataclass
class _Ayat:
    number: str                      # "" untuk teks pasal tanpa ayat
    lines: List[str] = field(default_factory=list)
    huruf: List[str] = field(default_factory=list)

    def text(self) -> str:
        return _join_lines(self.lines)


@dataclass
class _Pasal:
    number: str
    bab: str
    bab_title: str
    bagian: str
    bagian_title: str
    paragraf: str
    paragraf_title: str
    section: str                     # "batang_tubuh" | "penjelasan"
    ayat: List[_Ayat] = field(default_factory=list)


def _roman_to_int(roman: str) -> int:
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
    total, prev = 0, 0
    for ch in reversed(roman.upper()):
        v = values.get(ch, 0)
        total = total - v if v < prev else total + v
        prev = max(prev, v)
    return total


def _pasal_key(number: str) -> tuple:
    m = re.match(r'(\d+)([A-Z]?)', number)
    return (int(m.group(1)), m.group(2)) if m else (0, "")


def _normalize_line(line: str) -> str:
    line = _MD_PREFIX_RE.sub("", line)
    line = _MD_SUFFIX_RE.sub("", line)
    return re.sub(r'\s+', ' ', line).strip()


def _join_lines(lines: List[str]) -> str:
    text = " ".join(l for l in lines if l)
    return re.sub(r'\s+', ' ', text).strip()


class HierarchicalChunker:
    """
    Contoh:
        chunker = HierarchicalChunker(max_chars=1800)
        chunks = chunker.chunk(text, base_metadata={
            "regulator": "BI", "document": "PBI 23/6/PBI/2021",
        })
        # chunks: list[{"text": str, "metadata": dict}]
    """

    def __init__(self, max_chars: int = 1800, include_penjelasan: bool = True):
        self.max_chars = max_chars
        self.include_penjelasan = include_penjelasan

    # ------------------------------------------------------------------
    def chunk(self, text: str, base_metadata: Optional[Dict] = None) -> List[Dict]:
        base = dict(base_metadata or {})
        preamble, pasals, closing = self._parse(text)

        chunks: List[Dict] = []
        chunks.extend(self._free_text_chunks(preamble, "pembukaan", base))
        for pasal in pasals:
            if pasal.section == "penjelasan" and not self.include_penjelasan:
                continue
            chunks.extend(self._pasal_chunks(pasal, base))
        chunks.extend(self._free_text_chunks(closing, "penutup", base))

        for i, c in enumerate(chunks):
            c["metadata"]["chunk_index"] = i
        return chunks

    # ------------------------------------------------------------------
    def _parse(self, text: str):
        lines = [_normalize_line(l) for l in text.splitlines()]
        lines = [l for l in lines if l and not _PAGE_NUM_RE.match(l)]

        preamble: List[str] = []
        closing: List[str] = []
        pasals: List[_Pasal] = []

        bab = bab_title = bagian = bagian_title = paragraf = paragraf_title = ""
        section = "batang_tubuh"
        last_pasal = (0, "")
        last_bab = 0
        pending_title = None          # "bab" | "bagian" | "paragraf"
        current: Optional[_Pasal] = None
        in_closing = False

        def current_ayat() -> _Ayat:
            if not current.ayat:
                current.ayat.append(_Ayat(number=""))
            return current.ayat[-1]

        for line in lines:
            if _PENJELASAN_RE.match(line) and line.upper() == line:
                section = "penjelasan"
                in_closing = False
                current = None
                last_pasal = (0, "")
                last_bab = 0
                bab = bab_title = bagian = bagian_title = paragraf = paragraf_title = ""
                pending_title = None
                continue

            if section == "batang_tubuh" and _PENUTUP_RE.match(line):
                in_closing = True
                current = None
            if in_closing:
                closing.append(line)
                continue

            m = _BAB_RE.match(line)
            if m and _roman_to_int(m.group(1)) > last_bab:
                last_bab = _roman_to_int(m.group(1))
                bab, bab_title = f"BAB {m.group(1)}", m.group(2).strip()
                bagian = bagian_title = paragraf = paragraf_title = ""
                pending_title = None if bab_title else "bab"
                current = None
                continue

            m = _BAGIAN_RE.match(line)
            if m and (not m.group(2) or m.group(2)[0].isupper()):
                bagian, bagian_title = f"Bagian {m.group(1)}", m.group(2).strip()
                paragraf = paragraf_title = ""
                pending_title = None if bagian_title else "bagian"
                current = None
                continue

            m = _PARAGRAF_RE.match(line)
            if m:
                paragraf, paragraf_title = f"Paragraf {m.group(1)}", m.group(2).strip()
                pending_title = None if paragraf_title else "paragraf"
                current = None
                continue

            m = _PASAL_RE.match(line)
            if m:
                number = m.group(1) + m.group(2)
                key = _pasal_key(number)
                if key > last_pasal:
                    last_pasal = key
                    pending_title = None
                    current = _Pasal(
                        number=number, bab=bab, bab_title=bab_title,
                        bagian=bagian, bagian_title=bagian_title,
                        paragraf=paragraf, paragraf_title=paragraf_title,
                        section=section,
                    )
                    pasals.append(current)
                    continue

            if pending_title and current is None:
                # Judul bisa terpotong ke beberapa baris: akumulasi hingga penanda berikutnya
                if pending_title == "bab":
                    bab_title = f"{bab_title} {line}".strip()
                elif pending_title == "bagian":
                    bagian_title = f"{bagian_title} {line}".strip()
                elif pending_title == "paragraf":
                    paragraf_title = f"{paragraf_title} {line}".strip()
                continue

            if current is None:
                if not pasals:
                    preamble.append(line)
                continue

            m = _AYAT_RE.match(line)
            if m:
                current.ayat.append(_Ayat(number=m.group(1)))
                if m.group(2):
                    current.ayat[-1].lines.append(m.group(2))
                continue

            m = _HURUF_RE.match(line)
            if m:
                letter = m.group(1) or m.group(2)
                ayat = current_ayat()
                ayat.huruf.append(letter)
                ayat.lines.append(f"{letter}. {m.group(3) or ''}".strip())
                continue

            current_ayat().lines.append(line)

        return preamble, pasals, closing

    # ------------------------------------------------------------------
    def _pasal_chunks(self, pasal: _Pasal, base: Dict) -> List[Dict]:
        ayat_list = [a for a in pasal.ayat if a.text()]
        if not ayat_list:
            return []
        body_all = " ".join(self._ayat_text(a) for a in ayat_list)
        if pasal.section == "penjelasan" and _CUKUP_JELAS_RE.match(body_all):
            return []

        groups: List[List[_Ayat]] = []
        current: List[_Ayat] = []
        size = 0
        for ayat in ayat_list:
            t = self._ayat_text(ayat)
            if current and size + len(t) > self.max_chars:
                groups.append(current)
                current, size = [], 0
            current.append(ayat)
            size += len(t) + 1
        if current:
            groups.append(current)

        chunks = []
        for group in groups:
            body = " ".join(self._ayat_text(a) for a in group)
            if len(body) <= self.max_chars or len(group) > 1:
                chunks.append(self._make_chunk(pasal, group, body, base))
            else:
                for part in self._split_long(body):
                    chunks.append(self._make_chunk(pasal, group, part, base))
        return chunks

    @staticmethod
    def _ayat_text(ayat: _Ayat) -> str:
        return f"({ayat.number}) {ayat.text()}" if ayat.number else ayat.text()

    def _split_long(self, body: str) -> List[str]:
        # Pecah di batas huruf ("a. ", "b. ") lalu di batas kalimat
        pieces = re.split(r'(?=\s[a-z]{1,2}\.\s)|(?<=[.;])\s+', body)
        out, buf = [], ""
        for p in pieces:
            if buf and len(buf) + len(p) > self.max_chars:
                out.append(buf.strip())
                buf = ""
            buf += (" " if buf else "") + p.strip()
        if buf.strip():
            out.append(buf.strip())
        return out

    def _make_chunk(self, pasal: _Pasal, group: List[_Ayat], body: str, base: Dict) -> Dict:
        ayat_numbers = [a.number for a in group if a.number]
        if not ayat_numbers:
            ayat_label = ""
        elif len(ayat_numbers) == 1:
            ayat_label = ayat_numbers[0]
        else:
            ayat_label = f"{ayat_numbers[0]}-{ayat_numbers[-1]}"
        huruf = ",".join(h for a in group for h in a.huruf)

        document = base.get("document", "")
        crumbs = [document] if document else []
        if pasal.section == "penjelasan":
            crumbs.append("Penjelasan")
        if pasal.bab:
            crumbs.append(f"{pasal.bab} {pasal.bab_title}".strip())
        if pasal.bagian:
            crumbs.append(f"{pasal.bagian} {pasal.bagian_title}".strip())
        if pasal.paragraf:
            crumbs.append(f"{pasal.paragraf} {pasal.paragraf_title}".strip())
        pasal_label = f"Pasal {pasal.number}"
        if ayat_label:
            pasal_label += f" ayat ({ayat_label})"
        crumbs.append(pasal_label)

        heading = f"Pasal {pasal.number}" + (f" Ayat {ayat_numbers[0]}" if ayat_numbers else "")
        metadata = {
            **base,
            "section": pasal.section,
            "bab": pasal.bab,
            "bab_title": pasal.bab_title,
            "bagian": pasal.bagian,
            "bagian_title": pasal.bagian_title,
            "paragraf": pasal.paragraf,
            "pasal": f"Pasal {pasal.number}",
            "ayat": f"Ayat {ayat_label}" if ayat_label else "",
            "huruf": huruf,
            # Kunci kompatibilitas dengan metadata_extractor / BM25 filter lama
            "pasal_number": pasal.number,
            "ayat_number": ayat_numbers[0] if ayat_numbers else "",
            "section_heading": heading,
            "chunk_strategy": "hierarchical",
        }
        return {"text": " | ".join(crumbs) + "\n" + body, "metadata": metadata}

    def _free_text_chunks(self, lines: List[str], section: str, base: Dict) -> List[Dict]:
        text = _join_lines(lines)
        if not text:
            return []
        document = base.get("document", "")
        label = "Pembukaan" if section == "pembukaan" else "Penutup"
        chunks = []
        for part in self._split_long(text):
            chunks.append({
                "text": (f"{document} | {label}\n" if document else f"{label}\n") + part,
                "metadata": {
                    **base, "section": section, "bab": "", "bab_title": "",
                    "bagian": "", "bagian_title": "", "paragraf": "",
                    "pasal": "", "ayat": "", "huruf": "",
                    "pasal_number": "", "ayat_number": "", "section_heading": label,
                    "chunk_strategy": "hierarchical",
                },
            })
        return chunks

