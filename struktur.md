# Struktur Proyek Interactive Park

File ini memberikan gambaran tentang struktur direktori dan file dalam proyek `interactive-park`, beserta fungsi masing-masing komponen untuk memudahkan pembacaan dan pemahaman sistem.

## 📂 Root Directory (Folder Utama)

- **`main.py`**
  File utama untuk menjalankan pipeline deteksi desktop/headless. Menginisialisasi video loader, deteksi pose, manajemen area (ROI), dan audio dalam sebuah loop utama.
- **`server.py`**
  File utama untuk menjalankan server web (FastAPI). Menyediakan API untuk konfigurasi, manajemen file media, antarmuka web, dan streaming video (MJPEG).
- **`config.yaml`**
  File konfigurasi utama yang menyimpan pengaturan aplikasi, seperti sumber video, threshold, dan koordinat area interaktif.
- **`requirements.txt`**
  Daftar pustaka atau dependensi Python yang dibutuhkan untuk menjalankan proyek ini.
- **`README.md`**
  Dokumentasi utama proyek yang berisi informasi umum, cara instalasi, dan cara menjalankan aplikasi.
- **`INTERACTIVE_DETECTION_PLAN.md`** & **`Interactive_Park_Base_Project.md`**
  Dokumen perencanaan, arsitektur, dan desain dari proyek taman interaktif.

---

## 📁 Direktori Modul (Sub-folder)

### 1. `app/`
Berisi logika yang menjembatani server web dan pipeline utama.
- **`monitor.py`**: Layanan (service) yang berjalan di latar belakang untuk server web, menangani streaming video ke frontend dan memonitor status pipeline.

### 2. `assets/`
Direktori tempat menyimpan file media (otomatis dibuat/diakses oleh sistem).
- **`videos/`**: Tempat menyimpan file video yang diunggah untuk simulasi.
- **`audio/`**: Tempat menyimpan file suara/SFX.

### 3. `audio/`
Menangani sistem suara atau audio interaktif.
- **`audio_manager.py`**: Mengontrol pemutaran suara latar (ambient) dan efek suara (SFX) berdasarkan interaksi pengunjung dengan area taman.

### 4. `config/`
Menangani pemuatan dan validasi pengaturan.
- **`settings.py`**: Memuat nilai dari `config.yaml` dan menyediakannya sebagai objek konfigurasi (Settings) yang mudah diakses oleh bagian program lain.

### 5. `detector/` & `pose/`
Berisi logika terkait computer vision dan kecerdasan buatan.
- **`pose_detector.py`**: Menggunakan model AI (seperti YOLOv8 Pose) untuk mendeteksi keberadaan orang dan kerangka/pose tubuh mereka di dalam setiap frame video.

### 6. `input/`
Menangani input data ke dalam sistem.
- **`video_loader.py`**: Mengatur pengambilan frame dari kamera (webcam/CCTV) atau file video (simulasi).

### 7. `interaction/`
Mengatur logika interaksi antara orang yang terdeteksi dengan area taman.
- **`area_manager.py`**: Mengelola data polygon dari berbagai area taman (seperti *garden*, *plant*) dan mengecek apakah ada bagian tubuh yang berada di dalam area tersebut.
- **`touch_manager.py`**: Menghitung durasi seseorang berada di sebuah area dan memicu *event* (seperti sentuhan) jika melewati batas waktu (threshold) tertentu.

### 8. `mapping/`
Berisi alat untuk pengaturan area interaktif.
- **`area_mapper.py`**: Antarmuka desktop (GUI) untuk menggambar dan memetakan polygon area (ROI) pada frame video secara langsung sebelum sistem berjalan.

### 9. `utils/`
Kumpulan fungsi utilitas (alat bantu) umum.
- **`logger.py`**: Mengatur format dan output log aplikasi agar informatif dan mudah di-debug.
- **`fps_counter.py`**: Menghitung dan menampilkan kecepatan pemrosesan frame video (Frames Per Second).

### 10. `web/`
Berisi file *front-end* untuk antarmuka dashboard admin berbasis browser.
- **`index.html`**: Halaman utama antarmuka pengguna web.
- **`styles.css`**: Pengaturan desain dan tata letak untuk antarmuka web.
- **`app.js`**: Logika Javascript di sisi klien (browser) untuk berkomunikasi dengan API `server.py`, menangani unggahan file, mengatur area, dan memuat stream video.

---

*File ini dibuat secara otomatis untuk membantu pengembang memahami arsitektur proyek `interactive-park`.*
