# Task Sentimen Sampel

Proyek analisis sentimen berbasis data sampel. Repository ini digunakan untuk menyimpan data, kode, dan hasil eksperimen terkait klasifikasi sentimen (positif, negatif, netral) dari teks berbahasa Indonesia.

## Struktur Proyek

```
.
├── data/           # Dataset sampel (mentah dan hasil pra-pemrosesan)
├── notebooks/      # Notebook eksplorasi dan eksperimen
├── src/            # Kode sumber (pra-pemrosesan, pelatihan model, evaluasi)
├── output/         # Hasil pelabelan (digenerate oleh skrip, tidak disimpan di git)
└── README.md
```

## Tujuan

- Mengumpulkan dan menyiapkan data sampel untuk analisis sentimen.
- Melatih dan mengevaluasi model klasifikasi sentimen.
- Mendokumentasikan alur kerja dan hasil eksperimen.

## Cara Memulai

1. Clone repository ini:
   ```bash
   git clone https://github.com/denisbahtiarr/task-sentimen-sampel.git
   cd task-sentimen-sampel
   ```
2. Siapkan environment Python dan install dependensi (akan ditambahkan seiring perkembangan proyek).
3. Jalankan skrip atau notebook sesuai kebutuhan.

## Pelabelan Feedback

`src/label_feedback.py` membaca `data/feedback.csv` dan memberi label `sentiment`
(positive/negative/neutral), `topic`, dan `severity` (critical/high/medium/low)
pada tiap baris berdasarkan aturan kata kunci, lalu memisahkan baris dengan
severity high/critical dari sisanya.

```bash
python3 src/label_feedback.py --input data/feedback.csv --outdir output
```

Output yang dihasilkan di `output/`:
- `labeled_feedback.csv` — semua baris dengan label lengkap
- `high_critical_feedback.csv` — baris severity high & critical (butuh perhatian segera)
- `other_feedback.csv` — baris severity low & medium

## Kontribusi

Kontribusi dan masukan sangat terbuka. Silakan buat branch baru dan ajukan pull request untuk perubahan yang diusulkan.
