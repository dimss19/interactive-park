# PRD - Interactive Park AI (Base Project)

## Tujuan

Membangun fondasi sistem Computer Vision untuk taman interaktif
menggunakan YOLO11 dan YOLO11 Pose.

Tahap pertama **tidak** membuat logika interaksi maupun training model.

------------------------------------------------------------------------

# Target Akhir

Sistem nantinya mampu:

-   Mendeteksi manusia
-   Mendeteksi skeleton
-   Mendeteksi tanaman/bunga
-   Menentukan apakah tangan menyentuh tanaman
-   Memutar ambience sesuai interaksi

------------------------------------------------------------------------

# Roadmap

## Milestone 1 --- Base Project

Target:

-   Struktur project
-   Video Loader
-   YOLO11 Detection
-   YOLO11 Pose
-   Bounding Box
-   Skeleton
-   FPS

Belum ada:

-   Audio
-   ROI
-   Touch Detection
-   State Machine

------------------------------------------------------------------------

## Milestone 2 --- Plant Detection

Tambahkan:

-   plant
-   flower

Output:

-   Bounding Box tanaman
-   Bounding Box bunga

------------------------------------------------------------------------

## Milestone 3 --- ROI

Buat area taman.

Trigger:

Jika person masuk ROI

↓

Play ambience taman

------------------------------------------------------------------------

## Milestone 4 --- Touch Detection

Gunakan:

-   Left Wrist
-   Right Wrist

Logika:

Wrist overlap dengan bounding box tanaman selama \>0.5 detik

↓

Trigger audio tanaman

------------------------------------------------------------------------

## Milestone 5 --- Audio Manager

Buat module:

-   Background ambience
-   Plant ambience
-   Cooldown
-   Stop audio

------------------------------------------------------------------------

## Milestone 6 --- State Machine

State:

IDLE

↓

PERSON_DETECTED

↓

AMBIENCE_PLAYING

↓

HAND_TOUCH

↓

SPECIAL_AUDIO

↓

COOLDOWN

↓

IDLE

------------------------------------------------------------------------

# Teknologi

-   Python 3.12+
-   OpenCV
-   Ultralytics YOLO11
-   YOLO11 Pose
-   NumPy
-   Pygame

------------------------------------------------------------------------

# Struktur Project

``` text
interactive-park/

├── assets/
│   ├── videos/
│   └── audio/
│
├── models/
│
├── detector/
│   ├── person_detector.py
│   ├── pose_detector.py
│   └── plant_detector.py
│
├── input/
│   └── video_loader.py
│
├── interaction/
│
├── audio/
│
├── config/
│
├── utils/
│
├── logs/
│
├── main.py
├── requirements.txt
└── README.md
```

------------------------------------------------------------------------

# Input

Tahap awal menggunakan video.

Folder:

``` text
assets/videos/
```

Buat VideoLoader dengan method:

-   load_video()
-   read_frame()
-   reset()
-   release()

Video dapat diganti menjadi webcam hanya melalui konfigurasi.

------------------------------------------------------------------------

# Module Person Detector

Model:

-   yolo11n.pt

Method:

-   load_model()
-   detect()
-   draw()

Output:

-   Person
-   Bounding Box
-   Confidence

------------------------------------------------------------------------

# Module Pose Detector

Model:

-   yolo11n-pose.pt

Output:

-   Skeleton
-   17 Keypoints
-   Left Wrist
-   Right Wrist

Method:

-   load_model()
-   detect()
-   draw()

------------------------------------------------------------------------

# Config

Simpan:

-   Camera/Video Source
-   Model Path
-   Confidence
-   FPS
-   ROI
-   Audio Path

------------------------------------------------------------------------

# Logging

Tampilkan:

-   Video Loaded
-   Model Loaded
-   FPS
-   Person Count
-   Skeleton Count
-   Error

------------------------------------------------------------------------

# Kualitas Kode

Gunakan:

-   OOP
-   Type Hint
-   Docstring
-   Modular
-   Clean Code
-   Production Ready

------------------------------------------------------------------------

# Training

Belum dilakukan.

Gunakan model pretrained:

-   yolo11n.pt
-   yolo11n-pose.pt

Training hanya dilakukan jika:

-   Plant tidak terdeteksi
-   Flower tidak terdeteksi
-   Membutuhkan objek custom

------------------------------------------------------------------------

# Alur Sistem

``` text
Video
    │
    ▼
YOLO Person Detection
    │
    ▼
YOLO Pose
    │
    ▼
Draw Bounding Box
    │
    ▼
Draw Skeleton
    │
    ▼
FPS
```

Tahap berikutnya:

``` text
Video
    │
    ▼
Person Detection
    │
    ▼
Pose Detection
    │
    ▼
Plant Detection
    │
    ▼
ROI
    │
    ▼
Touch Detection
    │
    ▼
State Machine
    │
    ▼
Audio Trigger
```

------------------------------------------------------------------------

# Catatan

1.  Jangan melakukan training terlebih dahulu.
2.  Pastikan model pretrained berjalan stabil.
3.  Validasi skeleton pada video.
4.  Tambahkan ROI.
5.  Tambahkan deteksi tanaman.
6.  Implementasikan touch detection.
7.  Terakhir implementasikan audio dan optimasi.
