# Rencana Pengembangan Interactive Plant Detection

## 1. Tujuan

Membangun pengalaman taman interaktif dengan satu kamera atau video. Operator dapat memetakan batas taman serta beberapa zona bunga/tanaman. Ketika tangan pengunjung masuk dan bertahan di dalam zona tanaman, sistem memainkan SFX yang terhubung dengan zona tersebut.

Target pengalaman:

1. Pengunjung memasuki area taman.
2. Sistem mendeteksi tubuh dan posisi tangan.
3. Tangan mendekati lalu masuk ke zona tanaman.
4. Zona memberi umpan balik visual.
5. Setelah sentuhan tervalidasi, SFX tanaman diputar satu kali.
6. Zona harus dilepas dan melewati cooldown sebelum bisa dipicu kembali.

## 2. Ruang Lingkup

### Termasuk dalam versi pertama

- Satu webcam, RTSP stream, atau file video.
- Satu area utama bertipe `garden`.
- Jumlah zona `plant` yang dinamis, tidak dibatasi hanya kiri dan kanan.
- Polygon mapping melalui tampilan kamera.
- Deteksi left wrist dan right wrist dari YOLO Pose.
- SFX berbeda untuk setiap zona tanaman.
- Debounce, dwell time, release delay, dan cooldown.
- Overlay untuk status zona dan tangan.
- Status event pada dashboard lokal.
- Penyimpanan mapping ke YAML.
- Log event untuk kebutuhan tuning dan evaluasi.

### Belum menjadi prioritas

- Multi-camera.
- Pengenalan jenis tanaman otomatis.
- Tracking pengunjung lintas kamera.
- Penyimpanan atau rekaman video 24 jam.
- Cloud server atau kontrol dari internet.

## 3. Kondisi Project Saat Ini

Fondasi yang sudah tersedia:

- `AreaMapper` untuk menggambar polygon.
- `AreaManager` untuk memuat dan memeriksa posisi terhadap polygon.
- `PoseDetector` untuk bounding box dan keypoint tubuh.
- `TouchManager` untuk left/right wrist dan validasi sentuhan 0,5 detik.
- `AudioManager` untuk memuat dan memainkan SFX.
- FastAPI dan dashboard lokal untuk preview serta status.

Kesenjangan yang perlu ditutup:

- Mapper masih menggunakan empat area tetap.
- Relasi zona tanaman ke SFX belum eksplisit.
- State sentuhan belum memiliki release delay dan cooldown yang matang.
- Kedua tangan belum dibedakan dalam event.
- Belum ada tracking ID untuk membedakan beberapa pengunjung.
- Polygon masih memakai koordinat pixel sehingga sensitif terhadap perubahan resolusi.
- Mapping belum dapat dikelola dari dashboard.
- Belum ada overlay status `hover`, `triggered`, dan `cooldown`.

## 4. Alur Sistem

```text
Camera / Video
      |
      v
Frame Capture
      |
      +-----------------------> Preview Dashboard
      |
      v
YOLO Pose Detection
      |
      v
Person Tracking + Wrist Smoothing
      |
      v
Garden Gate Validation
      |
      v
Plant Polygon Collision
      |
      v
Touch State Machine
      |
      +--------> Visual Feedback / Dashboard Event
      |
      v
SFX Router -> AudioManager -> Speaker
```

Deteksi tangan hanya diproses untuk orang yang berada di dalam area `garden`. Hal ini mengurangi trigger dari orang yang terlihat di luar area interaktif.

## 5. Konsep Mapping

### 5.1 Jenis area

| Type | Fungsi |
|---|---|
| `garden` | Gerbang utama; interaksi hanya aktif ketika pengunjung berada di area ini. |
| `plant` | Zona yang dapat disentuh dan memiliki SFX sendiri. |
| `ignore` | Area yang diabaikan, misalnya layar, refleksi, atau jalur staf. |

### 5.2 Alur operator

1. Pilih sumber webcam atau video.
2. Ambil frame referensi dari kamera.
3. Buat atau edit area utama `garden`.
4. Tambahkan zona tanaman dengan tombol **Tambah Tanaman**.
5. Klik minimal tiga titik untuk membentuk polygon.
6. Isi nama dan ID zona yang unik.
7. Pilih SFX, volume, dwell time, dan cooldown.
8. Simpan dan jalankan mode uji.
9. Gerakkan tangan pada preview untuk memvalidasi polygon.

### 5.3 Aturan mapping

- Setiap area harus mempunyai minimal tiga titik.
- ID menggunakan format stabil seperti `plant_orchid_01`.
- Nama tampilan dapat diubah tanpa mengubah ID.
- Titik disimpan sebagai koordinat ternormalisasi `0.0-1.0`, bukan pixel absolut.
- Polygon tanaman boleh berada di dalam area taman.
- Jika dua polygon bertumpuk, pilih zona dengan prioritas tertinggi lalu area terkecil.
- Sediakan undo, reset, delete, rename, dan preview.
- Simpan backup konfigurasi sebelum mapping lama ditimpa.

Contoh normalisasi:

```text
normalized_x = pixel_x / frame_width
normalized_y = pixel_y / frame_height
```

Ketika dipakai, koordinat dikonversi kembali berdasarkan resolusi frame aktif. Mapping tetap konsisten apabila preview dan inference menggunakan ukuran berbeda dengan rasio aspek yang sama.

## 6. Strategi Deteksi Tangan

### 6.1 Keypoint

Gunakan keypoint YOLO Pose:

- Index 9: left wrist.
- Index 10: right wrist.
- Wrist hanya valid jika confidence memenuhi `min_wrist_confidence`.

### 6.2 Smoothing

Posisi wrist dapat meloncat antar-frame. Terapkan exponential moving average per orang dan per tangan:

```text
smoothed = alpha * current + (1 - alpha) * previous
```

Nilai awal `alpha = 0.45`. Posisi mentah tetap dapat ditampilkan pada mode debug.

### 6.3 Tracking orang

Gunakan ID tracker agar timer sentuhan milik satu pengunjung tidak berpindah ke pengunjung lain. State key yang disarankan:

```text
(camera_id, track_id, hand, zone_id)
```

Pada satu kamera, implementasi awal dapat memakai tracker Ultralytics dengan state persisten. Bila tracking belum siap, fase MVP boleh memakai state per zona, tetapi harus dicatat bahwa dua orang bersamaan belum dapat dibedakan dengan baik.

### 6.4 Collision

Sebuah tangan dianggap berada dalam zona apabila titik wrist yang sudah dihaluskan berada di dalam polygon menggunakan `cv2.pointPolygonTest`.

Untuk pengalaman yang lebih mudah dipicu, zona interaksi dapat mempunyai `hitbox_padding_px`. Padding hanya memperbesar area collision dan tidak mengubah polygon visual.

## 7. Touch State Machine

Setiap kombinasi orang, tangan, dan zona memiliki state berikut:

```text
OUTSIDE
   |
   | wrist masuk polygon
   v
HOVERING
   |
   | bertahan >= dwell_ms
   v
TRIGGERED -----------> COOLDOWN
   |                       |
   | wrist keluar          | cooldown selesai + wrist di luar
   v                       |
RELEASING -----------------+
```

### Definisi state

| State | Arti | Respons visual |
|---|---|---|
| `OUTSIDE` | Tidak ada tangan pada zona. | Polygon warna normal. |
| `HOVERING` | Tangan masuk, timer validasi berjalan. | Polygon menyala dan progress bertambah. |
| `TRIGGERED` | Dwell time terpenuhi dan event dikirim. | Flash/highlight dan SFX diputar. |
| `RELEASING` | Tangan baru keluar; menunggu release stabil. | Highlight meredup. |
| `COOLDOWN` | Trigger dikunci sementara. | Indikator cooldown. |

### Aturan anti-trigger palsu

- `dwell_ms`: tangan harus berada di zona terus-menerus, default 450 ms.
- `release_ms`: tangan harus berada di luar secara stabil, default 250 ms.
- `cooldown_ms`: zona tidak dapat dipicu kembali, default 3000 ms.
- `lost_track_grace_ms`: keypoint hilang singkat tidak langsung dianggap release, default 200 ms.
- SFX diputar ketika transisi `HOVERING -> TRIGGERED`, bukan setiap frame.
- Secara default satu zona hanya memainkan satu instance SFX pada satu waktu.
- Zona baru boleh retrigger setelah tangan keluar dan cooldown selesai.

## 8. Routing SFX

Setiap zona menyimpan `sfx_id`. Touch Manager hanya menghasilkan event dan tidak memutar audio secara langsung. `SfxRouter` menerjemahkan event menjadi perintah untuk `AudioManager`.

```text
TouchEvent(zone_id, hand, track_id, timestamp)
                    |
                    v
             SfxRouter lookup
                    |
                    v
        AudioManager.play(sfx_id)
```

Kebijakan audio yang perlu tersedia:

- `restart`: ulangi SFX dari awal saat retrigger.
- `ignore_if_playing`: abaikan trigger jika suara masih berjalan.
- `max_instances`: batasi suara yang sama secara bersamaan.
- `volume`: volume per SFX dikalikan master volume.
- `fade_in_ms` dan `fade_out_ms`: opsional untuk ambience.
- `priority`: SFX penting dapat menghentikan SFX berprioritas rendah.

## 9. Rancangan Konfigurasi

```yaml
interaction:
  enabled: true
  min_wrist_confidence: 0.45
  smoothing_alpha: 0.45
  lost_track_grace_ms: 200
  default_dwell_ms: 450
  default_release_ms: 250
  default_cooldown_ms: 3000

areas:
  garden_main:
    id: garden_main
    name: Main Garden
    type: garden
    polygon_normalized:
      - [0.05, 0.08]
      - [0.95, 0.08]
      - [0.95, 0.95]
      - [0.05, 0.95]

  plant_orchid_01:
    id: plant_orchid_01
    name: Orchid
    type: plant
    priority: 10
    polygon_normalized:
      - [0.08, 0.20]
      - [0.30, 0.18]
      - [0.33, 0.76]
      - [0.06, 0.78]
    interaction:
      sfx_id: orchid_bloom
      dwell_ms: 500
      release_ms: 250
      cooldown_ms: 3500
      hitbox_padding_px: 8

audio:
  enabled: true
  master_volume: 0.8
  sfx:
    orchid_bloom:
      path: assets/audio/orchid_bloom.ogg
      volume: 0.9
      loop: false
      policy: ignore_if_playing
      max_instances: 1
```

Jaga kompatibilitas sementara dengan field `polygon` berbasis pixel. Loader membaca `polygon_normalized` terlebih dahulu, lalu fallback ke `polygon` selama masa migrasi.

## 10. Perubahan Modul

### `mapping/area_mapper.py`

- Menghapus daftar area plant yang hard-coded.
- Menambah create, rename, delete, dan select zone dinamis.
- Menyimpan polygon ternormalisasi.
- Menambah pemilihan SFX dan parameter interaksi.
- Memvalidasi polygon sebelum penyimpanan.

### `interaction/area_manager.py`

- Mendukung koordinat ternormalisasi.
- Menyediakan lookup area berdasarkan ID.
- Menangani overlap berdasarkan priority dan luas polygon.
- Menyediakan optional hitbox padding.

### `interaction/touch_manager.py`

- Menggunakan class/enum state yang eksplisit.
- Memisahkan state berdasarkan track ID, hand, dan zone ID.
- Menambahkan dwell, release, cooldown, serta lost-track grace.
- Menghasilkan event terstruktur dan tidak bergantung langsung pada audio.

### `audio/audio_manager.py`

- Menambahkan policy playback dan limit instance.
- Menyediakan informasi durasi dan status channel.
- Menangani file tidak ada tanpa menghentikan pipeline.

### `app/monitor.py`

- Menghubungkan tracker, touch state, event, overlay, dan SFX router.
- Menyediakan snapshot status thread-safe untuk API.
- Memublikasikan event terbaru ke dashboard.

### Dashboard FastAPI

- Mode Mapping dan mode Run dipisahkan jelas.
- Daftar zona beserta SFX dan state real-time.
- Tombol test SFX.
- Tombol enable/disable interaction.
- Debug overlay untuk wrist confidence, track ID, timer, dan cooldown.

## 11. Model Event

```json
{
  "event": "plant_touch",
  "timestamp": "2026-07-16T10:20:30.120+07:00",
  "camera_id": "camera_01",
  "track_id": 7,
  "hand": "right",
  "zone_id": "plant_orchid_01",
  "sfx_id": "orchid_bloom",
  "dwell_ms": 512,
  "wrist_confidence": 0.87
}
```

Event minimum yang dicatat:

- `zone_enter`
- `plant_touch`
- `zone_release`
- `sfx_played`
- `sfx_failed`
- `camera_offline`

Log tuning sebaiknya dapat dimatikan pada production agar tidak terlalu besar.

## 12. Tahapan Implementasi

### Milestone 1 — Mapping dinamis

- Refactor mapper agar plant zone dapat ditambah dan dihapus.
- Simpan polygon ternormalisasi.
- Tambahkan ID, nama, warna, dan SFX per zona.
- Validasi dan backup konfigurasi.

**Selesai jika:** operator dapat membuat minimal lima zona tanpa mengubah kode.

### Milestone 2 — Touch state yang stabil

- Implementasi state machine.
- Tambahkan smoothing, dwell, release, cooldown, dan lost-track grace.
- Bedakan left/right hand pada event.
- Tambahkan unit test berbasis urutan keypoint sintetis.

**Selesai jika:** tangan yang hanya melintas cepat tidak memicu SFX dan tangan yang bertahan memicu tepat satu kali.

### Milestone 3 — SFX per tanaman

- Tambahkan `SfxRouter`.
- Implementasi policy playback.
- Tampilkan status file dan mixer.
- Tambahkan test SFX dari dashboard.

**Selesai jika:** setiap zona dapat memainkan SFX berbeda dan file yang hilang menghasilkan error terkontrol.

### Milestone 4 — Interactive feedback

- Overlay state dan progress dwell.
- Warna zona berubah berdasarkan state.
- Tampilkan titik wrist, confidence, serta track ID pada mode debug.
- Publikasikan event ke dashboard secara real-time.

**Selesai jika:** operator dapat memahami alasan suatu sentuhan dipicu atau ditolak hanya dari overlay.

### Milestone 5 — Tuning dan reliability

- Uji video siang, malam, ramai, dan tangan tertutup sebagian.
- Jalankan soak test minimal delapan jam.
- Ukur latency dari tangan masuk hingga suara mulai.
- Tambahkan recovery kamera dan audio device.
- Dokumentasikan preset threshold berdasarkan kondisi lokasi.

**Selesai jika:** sistem stabil selama jam operasional dan memenuhi acceptance criteria.

## 13. Strategi Pengujian

### Unit test

- Point berada di dalam, luar, dan tepat di tepi polygon.
- Polygon normalized dikonversi dengan benar.
- Dwell kurang dari threshold tidak menghasilkan touch.
- Dwell melewati threshold menghasilkan satu touch.
- Wrist hilang sesaat masih mempertahankan state.
- Release dan cooldown mencegah retrigger cepat.
- Overlap zona memilih priority yang benar.
- SFX yang tidak ditemukan tidak membuat aplikasi berhenti.

### Integration test

- Video -> pose -> wrist -> polygon -> event -> SFX.
- Reload konfigurasi mapping.
- Dashboard menerima state yang sesuai.
- Video selesai lalu looping tanpa mereset konfigurasi.

### Uji lapangan

- Satu orang dengan satu tangan.
- Satu orang dengan kedua tangan.
- Dua orang pada zona berbeda.
- Dua orang pada zona sama.
- Tangan bergerak cepat melewati tanaman.
- Tangan diam di tepi polygon.
- Tubuh berada di luar garden tetapi tangan terlihat di plant.
- Keypoint hilang akibat occlusion.

## 14. Acceptance Criteria

- Operator dapat membuat, mengedit, dan menghapus zona tanaman tanpa mengubah source code.
- Setiap zona dapat memiliki SFX dan threshold sendiri.
- Trigger hanya aktif ketika pengunjung memenuhi aturan garden gate.
- Gerakan melintas lebih singkat dari dwell time tidak memicu suara.
- Satu sentuhan stabil memicu maksimal satu SFX hingga release dan cooldown selesai.
- Latency target dari dwell terpenuhi sampai audio mulai kurang dari 200 ms, di luar waktu dwell.
- Tidak ada crash ketika SFX hilang, audio device tidak tersedia, atau keypoint menghilang.
- Mapping tetap sesuai saat pipeline memakai resolusi berbeda dengan rasio aspek sama.
- Dashboard menunjukkan state zona, tangan, dan error dengan jelas.
- Sistem dapat berjalan minimal delapan jam tanpa pertumbuhan memori yang terus-menerus.

## 15. Urutan Prioritas

Urutan kerja yang direkomendasikan:

1. Mapping plant dinamis dan koordinat normalized.
2. Event model dan touch state machine.
3. SFX routing per zona.
4. Overlay/debug feedback.
5. Tracking multi-person.
6. Dashboard mapping penuh.
7. Tuning performa dan uji lapangan.

Fokus pertama adalah membuat interaksi satu orang dan satu kamera terasa stabil. Multi-person dan multi-camera ditambahkan setelah event, mapping, dan audio contract sudah konsisten.
