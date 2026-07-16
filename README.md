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

Untuk komputer tanpa CUDA:

```yaml
models:
  pose_device: cpu
  pose_half: false
```

### 4. Aktifkan overlay saat testing

Overlay membantu melihat skeleton, polygon, dan status area:

```yaml
display:
  draw_debug_overlay: true
  draw_pose_overlay: true
```

Nonaktifkan overlay setelah mapping dan threshold sudah stabil untuk mengurangi beban pemrosesan.

### 5. Jalankan server

Dari root project, jalankan:

```powershell
python server.py
```

Jika berhasil, buka alamat berikut pada browser:

```text
http://127.0.0.1:8000
```

Dashboard menampilkan:

- Preview video.
- Status sumber online atau offline.
- Resolusi sumber.
- FPS pemrosesan.
- Jumlah orang yang terdeteksi.
- Area taman dan tanaman yang aktif.
- Status file serta tombol pengujian SFX.

Klik **Periksa sumber** untuk memastikan video dapat dibuka dan dibaca.

Status juga dapat diperiksa melalui API:

```text
http://127.0.0.1:8000/api/source/check
http://127.0.0.1:8000/api/status
```

Dokumentasi API tersedia di:

```text
http://127.0.0.1:8000/docs
```

Hentikan server dengan menekan `Ctrl+C` pada terminal.

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

Gunakan konfigurasi CPU:

```yaml
models:
  pose_device: cpu
  pose_half: false
```

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
