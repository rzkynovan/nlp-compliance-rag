"""
build_dataset.py — Bangun dataset untuk SOP Gate Classifier.

Mengumpulkan contoh positif (klausa SOP valid) dan negatif (bukan klausa SOP)
dari berbagai sumber, lalu simpan ke data/classifier/dataset.csv.

Label:
  1 = klausa SOP (layak diaudit RAG)
  0 = bukan klausa SOP (tolak sebelum masuk RAG)

Usage:
    python src/classifier/build_dataset.py
"""

import csv
import random
import sys
from pathlib import Path

OUTPUT_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "classifier" / "dataset.csv"


# ── Positive examples (klausa SOP / T&C e-wallet yang valid) ─────────────────

POSITIVE_EXAMPLES = [
    # Dari SOP Dummy NusantaraPay (golden dataset)
    "Perusahaan wajib memperoleh persetujuan tertulis atau persetujuan elektronik (explicit consent) dari Nasabah sebelum mengumpulkan dan memproses Data Pribadi.",
    "Data Pribadi Nasabah akan dienkripsi menggunakan standar keamanan AES-256 baik saat in-transit maupun at-rest.",
    "Nasabah berhak untuk meminta penghapusan permanen (Right to Erasure) atas Data Pribadi mereka kapan saja melalui aplikasi.",
    "Data Pribadi Nasabah tidak akan pernah dijual kepada pihak ketiga mana pun tanpa izin eksplisit yang terpisah.",
    "Penyelesaian pengaduan tertulis akan diselesaikan dalam waktu maksimal 60 hari kerja sejak pengaduan diterima.",
    "Layanan pengaduan tersedia setiap hari Senin hingga Jumat pukul 09.00 - 14.00 WIB.",
    "Pembekuan sementara akun akan dilakukan secara otomatis bagi pengguna yang memberikan rating bintang 1 pada aplikasi tanpa pemberitahuan sebelumnya.",
    "Batas maksimum saldo yang dapat disimpan dalam dompet digital untuk akun yang belum diverifikasi (unverified) adalah sebesar Rp10.000.000.",
    "Batas maksimum saldo yang dapat disimpan dalam dompet digital untuk akun yang telah diverifikasi (verified) adalah sebesar Rp500.000.000.",
    "Tidak ada batasan jumlah transaksi masuk bulanan bagi pengguna baik yang telah terverifikasi maupun yang belum terverifikasi.",
    "Ketentuan umum ini berlaku bagi seluruh pengguna layanan NusantaraPay.",
    "Penggunaan layanan ini tunduk pada hukum yang berlaku di Republik Indonesia.",

    # Dari T&C GoPay (sampel representatif)
    "GoPay berhak untuk mengubah, menangguhkan, atau menghentikan layanan atau fitur apapun dari GoPay, baik sebagian maupun seluruhnya, sewaktu-waktu dan untuk alasan apapun.",
    "Pengguna bertanggung jawab untuk menjaga kerahasiaan PIN, OTP, dan kredensial akun GoPay.",
    "GoPay tidak bertanggung jawab atas kerugian yang timbul akibat keterlambatan, kegagalan, atau gangguan dalam penyediaan layanan yang disebabkan oleh hal-hal di luar kendali GoPay.",
    "Pengguna dapat mengajukan pengaduan melalui layanan pelanggan GoPay yang tersedia 24 jam sehari, 7 hari seminggu.",
    "GoPay berhak untuk menutup atau menangguhkan akun Pengguna jika terdapat dugaan aktivitas penipuan atau pelanggaran terhadap Syarat dan Ketentuan ini.",
    "Pengguna memberikan kuasa yang tidak dapat ditarik kembali (irrevocable) kepada GoPay untuk melakukan debit dan/atau kredit saldo GoPay Pengguna.",
    "Batas transaksi harian untuk akun yang belum terverifikasi adalah Rp2.000.000 per transaksi.",
    "Saldo GoPay yang tidak digunakan selama 12 bulan berturut-turut akan dikenakan biaya administrasi sebesar Rp1.000 per bulan.",
    "Pengguna dapat melakukan top up saldo GoPay melalui berbagai metode pembayaran yang tersedia, termasuk transfer bank, kartu kredit, dan gerai mitra.",
    "GoPay berhak menggunakan data transaksi Pengguna untuk keperluan analisis internal dan peningkatan layanan.",
    "Pengguna setuju bahwa GoPay dapat berbagi data Pengguna dengan perusahaan afiliasi dalam Grup Gojek untuk tujuan operasional.",
    "Dalam hal terjadi sengketa, para pihak sepakat untuk menyelesaikannya melalui musyawarah mufakat terlebih dahulu.",
    "Pengguna wajib melengkapi proses verifikasi identitas (KYC) sebelum dapat menggunakan fitur transfer dana.",
    "GoPay tidak menjamin ketersediaan layanan 100% setiap saat dan berhak melakukan pemeliharaan sistem.",
    "Perubahan terhadap Syarat dan Ketentuan ini akan diberitahukan kepada Pengguna melalui aplikasi atau email.",
    "Pengguna yang melakukan transaksi mencurigakan dapat dilaporkan kepada otoritas terkait sesuai ketentuan AML/CFT.",
    "Layanan GoPay tunduk pada ketentuan Bank Indonesia dan Otoritas Jasa Keuangan yang berlaku.",
    "Pengguna bertanggung jawab atas semua transaksi yang dilakukan menggunakan akun GoPay mereka.",
    "GoPay berhak menolak, membatalkan, atau membalikkan transaksi yang dicurigai sebagai tindak penipuan.",
    "Penarikan saldo ke rekening bank dikenakan biaya administrasi sesuai ketentuan yang berlaku.",

    # Klausa SOP e-wallet umum (augmentasi)
    "Pengguna dapat mengajukan banding atas keputusan pemblokiran akun dalam waktu 14 hari kerja.",
    "Layanan pelanggan wajib memberikan nomor tiket pengaduan kepada setiap nasabah yang mengajukan keluhan.",
    "Transaksi yang gagal akibat gangguan sistem akan dikembalikan dalam waktu 1x24 jam.",
    "Pengguna diwajibkan untuk memperbarui informasi profil apabila terjadi perubahan data pribadi.",
    "Biaya administrasi bulanan sebesar Rp0 berlaku untuk semua tingkatan akun.",
    "Fitur auto-debit hanya dapat diaktifkan setelah pengguna memberikan persetujuan tertulis.",
    "Sistem akan mengirimkan notifikasi real-time untuk setiap transaksi yang melebihi Rp500.000.",
    "Pengguna dapat melihat riwayat transaksi selama 12 bulan terakhir melalui aplikasi.",
    "Dana yang dikirimkan ke akun yang tidak terdaftar akan dikembalikan dalam 3 hari kerja.",
    "Pengguna dengan akun terverifikasi dapat melakukan transaksi lintas negara dengan batas Rp50.000.000 per bulan.",
    "Layanan pembayaran tagihan tersedia untuk lebih dari 1.000 biller yang terdaftar.",
    "Penggunaan voucher atau promo hanya berlaku untuk transaksi yang memenuhi syarat dan ketentuan yang berlaku.",
    "Akun yang tidak aktif selama 24 bulan berturut-turut akan dinonaktifkan secara otomatis.",
    "Pemulihan akun yang diblokir memerlukan verifikasi identitas ulang melalui video call dengan petugas.",
    "Pengguna dapat menghubungkan akun e-wallet dengan rekening bank untuk kemudahan top up otomatis.",
    "Batas transfer ke sesama pengguna adalah Rp25.000.000 per hari untuk akun terverifikasi.",
    "Fitur split bill tersedia untuk transaksi grup dengan minimal 2 dan maksimal 20 pengguna.",
    "Program loyalitas memberikan poin reward untuk setiap transaksi senilai minimal Rp10.000.",
    "Pengguna dapat mengajukan pengembalian dana (refund) dalam waktu 30 hari setelah transaksi.",
    "Integrasi dengan marketplace memungkinkan pembayaran langsung tanpa meninggalkan aplikasi.",
    "Keamanan akun dilindungi dengan enkripsi end-to-end dan autentikasi dua faktor.",
    "Perusahaan wajib menyimpan data transaksi selama minimal 5 tahun sesuai ketentuan perpajakan.",
    "Pengguna dapat memilih bahasa tampilan antara Bahasa Indonesia dan Bahasa Inggris.",
    "Notifikasi promosi dapat dimatikan melalui pengaturan notifikasi di aplikasi.",
    "Akun bisnis dikenakan biaya MDR sebesar 0,7% untuk setiap transaksi masuk.",
    "Pelunasan cicilan yang terlambat dikenakan denda 2% per bulan dari jumlah tunggakan.",
    "Dana yang tersimpan dalam e-wallet dijamin keamanannya sesuai regulasi Bank Indonesia.",
    "Pengguna yang mengalami kehilangan perangkat dapat memblokir akun secara darurat melalui website.",
    "Setiap perubahan limit transaksi harus mendapat persetujuan dari pemegang akun melalui OTP.",
    "Layanan QR Code tersedia di lebih dari 5 juta merchant yang terdaftar di seluruh Indonesia.",
    "Pengguna dapat mendelegasikan akses terbatas kepada anggota keluarga melalui fitur akun keluarga.",
    "Sistem anti-fraud menggunakan machine learning untuk mendeteksi pola transaksi mencurigakan.",
    "Pengguna wajib melaporkan kehilangan atau pencurian perangkat dalam 24 jam untuk perlindungan penuh.",
    "Saldo minimum untuk melakukan penarikan tunai di ATM adalah Rp50.000.",
    "Pengguna dapat mengatur PIN 6 digit sebagai lapisan keamanan tambahan untuk transaksi besar.",
    "Transaksi internasional dikenakan biaya konversi mata uang sesuai kurs yang berlaku pada hari transaksi.",
    "Pengguna dapat mengajukan kenaikan limit transaksi dengan melengkapi dokumen verifikasi tambahan.",
    "Layanan escrow tersedia untuk transaksi jual beli online dengan nilai di atas Rp5.000.000.",
    "Pengguna dapat mengatur jadwal pembayaran otomatis untuk tagihan rutin hingga 12 bulan ke depan.",
    "Kebijakan privasi kami mematuhi ketentuan Undang-Undang Perlindungan Data Pribadi (UU PDP).",
]

# ── Negative examples (bukan klausa SOP) ─────────────────────────────────────

NEGATIVE_EXAMPLES = [
    # Greetings & percakapan
    "Halo selamat pagi",
    "Halo, bagaimana kabarmu hari ini?",
    "Selamat siang, apa yang bisa saya bantu?",
    "Hai! Saya ingin bertanya tentang sesuatu.",
    "Terima kasih banyak atas bantuannya.",
    "Oke baik, sampai jumpa!",
    "Hei, sudah lama tidak bertemu.",
    "Selamat malam, semoga harimu menyenangkan.",
    "Boleh tanya sesuatu nggak?",
    "Maaf mengganggu waktunya.",

    # Pertanyaan umum / factual
    "Apa itu inflasi?",
    "Berapa tinggi Gunung Everest?",
    "Siapa presiden Indonesia pertama?",
    "Kapan Indonesia merdeka?",
    "Bagaimana cara membuat nasi goreng?",
    "Apa perbedaan antara bank dan fintech?",
    "Mengapa langit berwarna biru?",
    "Berapa nilai tukar dolar hari ini?",
    "Di mana kantor pusat Bank Indonesia?",
    "Apa nama ibu kota Australia?",
    "Siapa penemu telepon?",
    "Berapa lama penerbangan Jakarta ke Tokyo?",
    "Apa yang dimaksud dengan GDP?",
    "Bagaimana cara kerja mesin pencari Google?",
    "Kapan musim hujan di Indonesia?",

    # Lirik lagu
    "Bila yang tertulis untukku adalah yang terbaik untukmu.",
    "Dan bila harus memilih aku akan tetap memilihmu.",
    "Laskar pelangi takkan terikat waktu.",
    "Mimpi adalah kunci untuk kita menaklukkan dunia.",
    "Ku berlari mengejarmu, namun tak bisa kugapai.",
    "Terjebak nostalgia, masa lalu yang indah.",
    "Kau adalah wanita tercantik yang pernah aku lihat.",
    "Jangan kau lepaskan tanganku selamanya.",
    "Aku mau mencintai kamu sampai mati.",
    "Bintang kejora di langit malam.",
    "Balonku ada lima, rupa-rupa warnanya.",
    "Dua mata saya, hidung saya satu.",

    # Berita dan narasi umum
    "Pemerintah Indonesia mengumumkan pertumbuhan ekonomi sebesar 5,1% pada kuartal ketiga tahun ini.",
    "Tim nasional sepak bola Indonesia berhasil memenangkan pertandingan melawan Malaysia dengan skor 3-1.",
    "Hujan lebat melanda Jakarta sejak pagi hari, menyebabkan banjir di beberapa titik.",
    "Presiden meresmikan jembatan baru yang menghubungkan Pulau Jawa dan Sumatera.",
    "Harga bahan bakar minyak resmi dinaikkan pemerintah mulai hari ini.",
    "Gempa bumi berkekuatan 6,2 SR mengguncang wilayah Sulawesi Tengah.",
    "Festival budaya tahunan kembali digelar setelah dua tahun absen akibat pandemi.",
    "Startup teknologi Indonesia berhasil meraih pendanaan seri C sebesar 100 juta dolar.",
    "Panen raya padi di Jawa Tengah mencapai rekor tertinggi dalam 10 tahun terakhir.",
    "Polisi berhasil menggagalkan penyelundupan narkoba senilai miliaran rupiah.",

    # Kalimat random / tidak bermakna
    "Lorem ipsum dolor sit amet consectetur adipiscing elit.",
    "The quick brown fox jumps over the lazy dog.",
    "1234567890",
    "test test test",
    "asdfghjkl",
    "abc def ghi jkl mno pqr stu vwx yz",
    "???",
    "...",
    "null",
    "undefined",

    # Pertanyaan teknis non-SOP
    "Bagaimana cara membuat website dengan React?",
    "Apa perbedaan antara Python dan JavaScript?",
    "Cara install Docker di Ubuntu?",
    "Error: cannot read property of undefined.",
    "SELECT * FROM users WHERE id = 1;",
    "git commit -m 'initial commit'",
    "pip install tensorflow",
    "import numpy as np",
    "function hello() { return 'world'; }",
    "def calculate_sum(a, b): return a + b",

    # Komentar / opini
    "Menurut saya aplikasi ini sangat bagus dan mudah digunakan.",
    "Pelayanannya buruk sekali, saya kecewa.",
    "Aplikasinya sering error dan lambat.",
    "Saya suka fitur split bill-nya, sangat membantu.",
    "Tolong perbaiki bug pada halaman transaksi.",
    "UI-nya perlu diperbarui agar lebih modern.",
    "Kenapa saldo saya berkurang tiba-tiba?",
    "Saya mau komplain soal transaksi yang gagal tapi uang terpotong.",
    "Kapan fitur investasi akan diluncurkan?",
    "Apakah ada promo cashback bulan ini?",

    # Kalimat deskriptif non-regulatori
    "Kucing adalah hewan peliharaan yang populer di seluruh dunia.",
    "Indonesia adalah negara kepulauan terbesar di dunia.",
    "Matematika adalah ilmu yang mempelajari bilangan dan operasinya.",
    "Olahraga teratur dapat meningkatkan kesehatan jantung dan paru-paru.",
    "Membaca buku adalah kebiasaan yang baik untuk meningkatkan pengetahuan.",
    "Pohon menghasilkan oksigen melalui proses fotosintesis.",
    "Air mendidih pada suhu 100 derajat Celsius di tekanan atmosfer normal.",
    "Bumi mengorbit matahari dalam waktu sekitar 365 hari.",
    "Vitamin C banyak ditemukan dalam buah jeruk dan lemon.",
    "Dinosaurus punah sekitar 66 juta tahun yang lalu.",
]


def build_dataset():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for text in POSITIVE_EXAMPLES:
        rows.append({"text": text.strip(), "label": 1})
    for text in NEGATIVE_EXAMPLES:
        rows.append({"text": text.strip(), "label": 0})

    random.seed(42)
    random.shuffle(rows)

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["text", "label"])
        writer.writeheader()
        writer.writerows(rows)

    pos = sum(1 for r in rows if r["label"] == 1)
    neg = sum(1 for r in rows if r["label"] == 0)
    print(f"Dataset tersimpan: {OUTPUT_PATH}")
    print(f"Total: {len(rows)} contoh — Positif (SOP): {pos}, Negatif: {neg}")


if __name__ == "__main__":
    build_dataset()
