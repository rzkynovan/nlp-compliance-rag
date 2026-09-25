"""Test HierarchicalChunker — Subbab 3.3.1 proposal."""

from retrieval.hierarchical_chunker import HierarchicalChunker

BASE = {"regulator": "BI", "document": "PBI 23/6/PBI/2021"}

PLAIN_TEXT = """PERATURAN BANK INDONESIA
NOMOR 23/6/PBI/2021
Menimbang : a. bahwa reformasi pengaturan sistem pembayaran
BAB I
KETENTUAN UMUM
Pasal 1
Dalam Peraturan Bank Indonesia ini yang dimaksud dengan:
1. Bank Indonesia adalah bank sentral.
- 2 -
BAB III
PENYELENGGARAAN SISTEM PEMBAYARAN
OLEH PJP
Bagian Kedelapan
Akses ke Sumber Dana
Paragraf 1
Akses ke Sumber Dana Berupa
Uang Elektronik
Pasal 160
(1)
Batas nilai uang elektronik yang dapat disimpan
ditetapkan sebagai berikut:
a.
untuk uang elektronik unregistered paling banyak
Rp2.000.000,00; dan
b.
untuk uang elektronik registered paling banyak
Rp10.000.000,00.
(2)
Batas nilai transaksi uang elektronik dalam 1 (satu)
bulan paling banyak Rp20.000.000,00. Lihat
Pasal 2
Pasal 161
Penyelenggara wajib mematuhi ketentuan sebagaimana dimaksud dalam Pasal 160.
Ditetapkan di Jakarta
pada tanggal 1 Juli 2021
PENJELASAN
ATAS PERATURAN BANK INDONESIA
Pasal 1
Cukup jelas.
Pasal 160
Ayat (1)
Cukup jelas.
Ayat (3)
Termasuk transaksi yang bersifat incoming antara lain top up.
"""

MARKDOWN_TEXT = """# PERATURAN OTORITAS JASA KEUANGAN
## BAB II KETENTUAN PELINDUNGAN KONSUMEN
### Bagian Kedua Perilaku Dasar PUJK
#### Paragraf 3 Pelindungan Data dan Informasi Konsumen
**Pasal 23**
(1) Ketentuan sebagaimana dimaksud dalam Pasal 22 ayat (1) dikecualikan.
(2) PUJK wajib menjelaskan secara tertulis dan/atau lisan mengenai tujuan.
(3) Dalam hal PUJK memperoleh data dari pihak lain, PUJK wajib:
a. memiliki pernyataan tertulis; dan
b. memberitahukan Konsumen mengenai sumber data.
"""


def _by_pasal(chunks, number, section="batang_tubuh"):
    return [c for c in chunks
            if c["metadata"]["pasal_number"] == number and c["metadata"]["section"] == section]


def test_hierarchy_metadata_plain_text():
    chunks = HierarchicalChunker().chunk(PLAIN_TEXT, BASE)
    [p160] = _by_pasal(chunks, "160")
    md = p160["metadata"]
    assert md["bab"] == "BAB III"
    assert md["bab_title"] == "PENYELENGGARAAN SISTEM PEMBAYARAN OLEH PJP"
    assert md["bagian"] == "Bagian Kedelapan"
    assert md["paragraf"] == "Paragraf 1"
    assert md["pasal"] == "Pasal 160"
    assert md["ayat"] == "Ayat 1-2"
    assert md["huruf"] == "a,b"
    assert md["document"] == "PBI 23/6/PBI/2021"
    # Breadcrumb hierarki ada di teks chunk
    assert p160["text"].startswith("PBI 23/6/PBI/2021 | BAB III")
    assert "Paragraf 1 Akses ke Sumber Dana Berupa Uang Elektronik" in p160["text"]
    assert "(1) Batas nilai uang elektronik" in p160["text"]
    assert "Rp2.000.000,00" in p160["text"]


def test_inline_pasal_reference_is_not_a_new_pasal():
    chunks = HierarchicalChunker().chunk(PLAIN_TEXT, BASE)
    # "Pasal 2" sendirian di satu baris (rujukan) tidak boleh memulai pasal baru
    assert not _by_pasal(chunks, "2")
    assert "Pasal 2" in _by_pasal(chunks, "160")[0]["text"]
    assert len(_by_pasal(chunks, "161")) == 1


def test_page_numbers_and_closing_are_separated():
    chunks = HierarchicalChunker().chunk(PLAIN_TEXT, BASE)
    assert all("- 2 -" not in c["text"] for c in chunks)
    sections = {c["metadata"]["section"] for c in chunks}
    assert {"pembukaan", "batang_tubuh", "penutup", "penjelasan"} <= sections
    [p161] = _by_pasal(chunks, "161")
    assert "Ditetapkan" not in p161["text"]


def test_penjelasan_cukup_jelas_dropped_and_tagged():
    chunks = HierarchicalChunker().chunk(PLAIN_TEXT, BASE)
    assert not _by_pasal(chunks, "1", section="penjelasan")
    [pj160] = _by_pasal(chunks, "160", section="penjelasan")
    assert "top up" in pj160["text"]
    assert "Penjelasan" in pj160["text"].split("\n")[0]

    no_pj = HierarchicalChunker(include_penjelasan=False).chunk(PLAIN_TEXT, BASE)
    assert all(c["metadata"]["section"] != "penjelasan" for c in no_pj)


def test_llamaparse_markdown_input():
    chunks = HierarchicalChunker().chunk(MARKDOWN_TEXT, {"regulator": "OJK", "document": "POJK 22/2023"})
    [p23] = _by_pasal(chunks, "23")
    md = p23["metadata"]
    assert md["bab"] == "BAB II"
    assert md["bagian"] == "Bagian Kedua"
    assert md["paragraf"] == "Paragraf 3"
    assert md["ayat"] == "Ayat 1-3"
    assert md["huruf"] == "a,b"
    assert "#" not in p23["text"] and "**" not in p23["text"]


def test_long_pasal_split_by_ayat_groups():
    ayat = "\n".join(f"({i})\n" + "ketentuan panjang " * 30 for i in range(1, 7))
    text = f"BAB I\nUMUM\nPasal 5\n{ayat}\n"
    chunks = HierarchicalChunker(max_chars=1200).chunk(text, BASE)
    p5 = _by_pasal(chunks, "5")
    assert len(p5) > 1
    assert all(len(c["text"].split("\n", 1)[1]) <= 1200 for c in p5)
    # Semua ayat tetap tercakup tepat sekali, berurutan
    labels = [c["metadata"]["ayat"] for c in p5]
    assert labels[0].startswith("Ayat 1") and labels[-1].endswith("6")


def test_metadata_values_are_chroma_compatible():
    chunks = HierarchicalChunker().chunk(PLAIN_TEXT, BASE)
    for c in chunks:
        for v in c["metadata"].values():
            assert isinstance(v, (str, int, float, bool))
