# Interactive Park AI

Sistem computer vision untuk taman interaktif menggunakan OpenCV, YOLO11 Pose, FastAPI, dan Pygame. Sistem membaca satu webcam atau video, mendeteksi posisi tubuh dan tangan, memeriksa interaksi dengan area tanaman, kemudian memainkan SFX yang sesuai.

## Persyaratan

- Python 3.10 atau lebih baru.
- Webcam atau file video untuk pengujian.
- GPU NVIDIA bersifat opsional, tetapi disarankan untuk inference real-time.
- Speaker atau audio output jika ingin menguji SFX.

## Instalasi

Disarankan menggunakan virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Pastikan model berikut tersedia:

```text
models/yolo11n-pose.pt
```

## Menjalankan dengan video testing

### 1. Siapkan video

Letakkan video pengujian di folder:

```text
assets/videos/
```

Project sudah menyediakan video contoh:

```text
assets/videos/sample.mp4
```

Format yang disarankan adalah MP4 dengan codec H.264. OpenCV juga dapat membaca format lain apabila codec tersedia pada komputer.

### 2. Pilih video

Buka `config.yaml`, kemudian isi `video_source` dengan lokasi video:

```yaml
video_source: assets/videos/sample.mp4
```

Untuk memakai video lain, salin file tersebut ke `assets/videos` dan ubah nilainya. Contoh:

```yaml
video_source: assets/videos/testing_taman_01.mp4
```

Jika nama file mengandung spasi, gunakan tanda kutip:

```yaml
video_source: "assets/videos/video taman.mp4"
```

Path dapat bersifat relatif terhadap root project atau absolut:

```yaml
video_source: "D:/video-testing/taman.mp4"
```

Video akan diputar ulang otomatis setelah mencapai frame terakhir ketika dijalankan melalui dashboard FastAPI.

### 3. Atur perangkat inference

Untuk komputer dengan GPU NVIDIA dan CUDA:

```yaml
models:
  pose_device: cuda:0
  pose_half: true
```

Untuk komputer tanpa CUDA (termasuk GPU AMD Radeon dan CPU saja):

PyTorch tidak menyediakan wheel ROCm untuk Windows, sehingga di Windows GPU AMD tidak dipakai oleh PyTorch. Inference berjalan di CPU.

```yaml
models:
  pose_device: cpu
  pose_half: false
```

Catatan untuk pengguna GPU AMD Radeon: di Linux, PyTorch ROCm dapat memakai GPU AMD, tetapi di Windows gunakan konfigurasi CPU di atas.

### 4. Aktifkan overlay saat testing

Overlay membantu melihat skeleton, polygon, dan status area:

```yaml
display:
  draw_debug_overlay: true
  draw_pose_overlay: true
```

Nonaktifkan overlay setelah mapping dan threshold sudah stabil untuk mengurangi beban pemrosesan.

Konfigurasi bawaan memproses pose setiap frame dengan target 30 FPS agar skeleton mengikuti orang dan posisi tangan terlihat saat masuk ke zona tanaman:

```yaml
target_fps: 30
models:
  detect_every_n_frames: 1
display:
  draw_debug_overlay: true
  draw_pose_overlay: true
```

Lingkaran biru muda menunjukkan posisi wrist. Ketika wrist masuk ke polygon tanaman, lingkaran berubah menjadi kuning dan label `TOUCH` ditampilkan. Nilai 30 FPS adalah target; FPS aktual bergantung pada GPU, resolusi video, dan ukuran model.

### 5. Jalankan server

Dari root project, jalankan:

```powershell
python server.py
```

Jika berhasil, buka alamat berikut pada browser:

```text
http://127.0.0.1:8080
```

Dashboard menampilkan:

- Preview video.
- Status sumber online atau offline.
- Resolusi sumber.
- FPS pemrosesan.
- Jumlah orang yang terdeteksi.
- Area taman dan tanaman yang aktif.
- Pemilihan webcam atau video tanpa mengedit YAML.
- Upload video testing.
- Editor polygon garden dan plant langsung di atas video.
- Upload, pengujian, dan penghapusan konfigurasi SFX.

Klik **Periksa sumber** untuk memastikan video dapat dibuka dan dibaca.

Status juga dapat diperiksa melalui API:

```text
http://127.0.0.1:8080/api/source/check
http://127.0.0.1:8080/api/status
```

Dokumentasi API tersedia di:

```text
http://127.0.0.1:8080/docs
```

Hentikan server dengan menekan `Ctrl+C` pada terminal.

## Mengatur semuanya melalui dashboard web

Setelah membuka `http://127.0.0.1:8080`, gunakan tab berikut:

### Video / Webcam

1. Pilih `Webcam 0`, `Webcam 1`, atau video yang tersedia.
2. Klik **Gunakan sumber**.
3. Untuk video baru, klik **Upload video**, tunggu hingga selesai, lalu pilih video tersebut dan klik **Gunakan sumber**.
4. Klik **Periksa sumber aktif** untuk memastikan frame dapat dibaca.

File video yang diunggah disimpan ke `assets/videos/`. Pergantian sumber disimpan ke `config.yaml` dan pipeline dimuat ulang secara otomatis.

### Mapping

1. Buka tab **Mapping**.
2. Klik **Buat semua area** untuk membuat preset Taman, Tanaman Kiri, Tanaman Kanan, dan Jalan sekaligus.
3. Klik tombol **Taman**, **Tanaman kiri**, **Tanaman kanan**, atau **Jalan** untuk memilih area yang ingin diedit.
4. Seret titik bulat pada polygon agar mengikuti batas objek pada video.
5. Polygon juga dapat dipilih dengan mengklik bagian dalam area tersebut.
6. Pilih SFX untuk area bertipe `plant`, lalu klik **Update data area**.
7. Klik **Simpan semua mapping** untuk menulis konfigurasi dan memuat ulang pipeline.

Gunakan **Reset posisi preset** jika polygon lama berada di luar video, **Gambar ulang** untuk membuat polygon bebas, **Undo titik** untuk membatalkan titik terakhir, **Update data area** untuk mengganti nama/tipe/SFX, dan **Hapus area** untuk menghapus polygon.

Fungsi area standar:

- **Taman**: batas utama tempat interaksi pengunjung diaktifkan.
- **Tanaman kiri**: area sentuhan tanaman pada sisi kiri video.
- **Tanaman kanan**: area sentuhan tanaman pada sisi kanan video.
- **Jalan**: batas jalur pengunjung yang dapat digunakan untuk visualisasi atau logika lanjutan.

### SFX

1. Buka tab **SFX**.
2. Isi ID SFX tanpa spasi, misalnya `orchid_bloom`.
3. Atur volume dan pilihan loop.
4. Pilih file OGG, WAV, atau MP3.
5. Klik **Simpan SFX**.
6. Gunakan tombol **Tes** untuk mendengarkan suara.
7. Kembali ke tab **Mapping**, pilih zona tanaman, lalu pilih SFX tersebut pada field **SFX tanaman**.
8. Klik **Update data area**, lalu **Simpan semua mapping**.

File audio yang diunggah disimpan ke `assets/audio/`. Menghapus SFX dari dashboard hanya menghapus konfigurasinya; file audio tetap disimpan agar tidak terjadi penghapusan data secara tidak sengaja.

## Menjalankan dengan webcam

Ubah `video_source` menjadi index webcam:

```yaml
video_source: 0
```

Jika komputer memiliki beberapa webcam, coba index berikutnya:

```yaml
video_source: 1
```

Simpan konfigurasi lalu restart `python server.py`. Jangan gunakan tanda kutip jika nilai tersebut dimaksudkan sebagai index webcam.

## Mapping area taman dan tanaman

Untuk membuka mode mapping lama berbasis OpenCV, atur:

```yaml
mapping:
  enabled: true
```

Lalu jalankan:

```powershell
python main.py
```

Kontrol mapping:

| Tombol | Fungsi |
|---|---|
| `1` | Pilih area taman. |
| `2` | Pilih tanaman kiri. |
| `3` | Pilih tanaman kanan. |
| `4` | Pilih walkway. |
| Klik kiri | Tambahkan titik polygon. |
| `Backspace` | Batalkan titik terakhir. |
| `R` | Reset area aktif. |
| `Enter` | Commit polygon aktif. |
| `S` | Simpan mapping. |
| `Q` | Simpan dan mulai deteksi. |

Mapping disimpan ke bagian `areas` dalam `config.yaml`. Rencana pengembangan mapping tanaman dinamis dijelaskan dalam `INTERACTIVE_DETECTION_PLAN.md`.

## Mengatur SFX

Letakkan file audio dalam folder:

```text
assets/audio/
```

Contoh konfigurasi:

```yaml
audio:
  enabled: true
  master_volume: 0.8
  cooldown_seconds: 5
  sfx:
    ambience:
      path: assets/audio/ambience.ogg
      volume: 0.5
      loop: true
    plant_touch:
      path: assets/audio/plant.ogg
      volume: 1.0
      loop: false
```

Keterangan:

- `enabled`: mengaktifkan atau menonaktifkan seluruh audio.
- `master_volume`: volume global dari `0.0` sampai `1.0`.
- `path`: lokasi file SFX.
- `volume`: volume individual SFX dari `0.0` sampai `1.0`.
- `loop`: `true` untuk mengulang suara, `false` untuk memutar satu kali.
- `cooldown_seconds`: jeda sebelum event audio dapat dipicu kembali.

Setelah mengubah konfigurasi atau menambahkan file audio, restart server. Gunakan tombol **Tes** pada dashboard untuk memastikan setiap SFX dapat dimainkan.

## Menjalankan mode desktop lama

Mode OpenCV tanpa dashboard masih tersedia:

```powershell
python main.py
```

Tekan `Q` pada jendela OpenCV untuk keluar.

## Troubleshooting

### Video berstatus offline

- Pastikan path di `video_source` benar.
- Jalankan perintah dari root project.
- Hindari backslash tunggal pada path YAML; gunakan `/`.
- Coba video MP4 H.264 jika codec video lain tidak terbaca.

### Webcam tidak dapat dibuka

- Tutup aplikasi lain yang sedang memakai webcam.
- Coba `video_source: 1` jika index `0` bukan kamera yang benar.
- Pastikan izin kamera Windows diberikan kepada aplikasi desktop.

### CUDA error

Gunakan konfigurasi CPU (juga berlaku untuk GPU AMD Radeon di Windows, karena PyTorch ROCm hanya tersedia di Linux):

```yaml
models:
  pose_device: cpu
  pose_half: false
```

Jika `pose_device` diset `cuda:0` namun tidak ada GPU NVIDIA, detector akan otomatis fallback ke CPU dan mencatat peringatan di log.

### SFX tidak berbunyi

- Pastikan file pada `audio.sfx` benar-benar tersedia.
- Pastikan `audio.enabled` bernilai `true`.
- Periksa status mixer dan file pada dashboard.
- Pastikan perangkat audio Windows aktif dan tidak sedang mute.

### FPS terlalu rendah

- Naikkan `models.detect_every_n_frames`, misalnya dari `5` menjadi `8`.
- Turunkan `models.pose_imgsz`.
- Nonaktifkan debug dan pose overlay.
- Gunakan GPU CUDA jika tersedia.
