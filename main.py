import cv2
import logging
import sys

from config.settings import Settings
from utils.logger import setup_logger
from utils.fps_counter import FPSCounter
from input.video_loader import VideoLoader
from pose.pose_detector import PoseDetector
from interaction.plant_zone import PlantZoneManager
from interaction.touch_manager import TouchManager
from audio.audio_manager import AudioManager

def main():
    logger = setup_logger()
    logger.info("Starting Interactive Park AI (Polygon ROI & Touch Detection)...")

    settings = Settings("config.yaml")

    video_loader = VideoLoader(settings.video_source)
    if not video_loader.load_video():
        logger.error("Could not load video source. Exiting.")
        sys.exit(1)

    pose_detector = PoseDetector(
        settings.pose_model_path,
        settings.confidence_threshold,
        imgsz=settings.pose_imgsz,
        device=settings.pose_device,
        half=settings.pose_half,
    )
    
    plant_zones = PlantZoneManager()
    plant_zones.load(settings.plant_zones)
    
    # We keep AudioManager around, though its logic might need adapting later
    audio_manager = AudioManager()
    
    fps_counter = FPSCounter()
    
    success, frame = video_loader.read_frame()
    if not success:
        logger.error("Could not read first frame.")
        sys.exit(1)

    frame_height, frame_width = frame.shape[:2]
    touch_manager = TouchManager(frame_width=frame_width, touch_duration_threshold=0.5, plant_zone_manager=plant_zones)

    logger.info("Initialization complete. Starting main loop.")
    
    if isinstance(settings.video_source, str):
        video_loader.reset()

    frame_count = 0

    try:
        while True:
            success, frame = video_loader.read_frame()
            if not success:
                logger.info("Video ended or cannot read frame.")
                break
                
            frame_count += 1
            fps_counter.tick()

            persons = pose_detector.detect(frame)
            
            # Touch Detection based on wrist inside the target plant polygon
            touch_manager.update(persons)
            
            # Drawing
            frame = pose_detector.draw(frame, persons)
            frame = plant_zones.draw(frame)
            frame = fps_counter.draw(frame)

            if frame_count % 30 == 0:
                logger.info(f"Frame {frame_count}: Person={len(persons)} | FPS: {fps_counter.get_fps():.1f}")

            import os
            headless = os.getenv("HEADLESS", "0") == "1"
            
            if not headless:
                cv2.imshow("Interactive Park AI", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    logger.info("Quit requested by user.")
                    break
            else:
                if frame_count >= 60:
                    logger.info("Headless testing finished (60 frames).")
                    break
                
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}")
    finally:
        logger.info("Cleaning up resources...")
        video_loader.release()
        if not os.getenv("HEADLESS", "0") == "1":
            cv2.destroyAllWindows()
        logger.info("Exited.")

if __name__ == "__main__":
    main()

