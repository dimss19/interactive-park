import cv2
import logging
import sys

from config.settings import Settings
from utils.logger import setup_logger
from utils.fps_counter import FPSCounter
from input.video_loader import VideoLoader
from detector.person_detector import PersonDetector
from detector.pose_detector import PoseDetector

def main():
    # Setup logging
    logger = setup_logger()
    logger.info("Starting Interactive Park AI...")

    # Load Settings
    settings = Settings("config.yaml")

    # Initialize Modules
    video_loader = VideoLoader(settings.video_source)
    if not video_loader.load_video():
        logger.error("Could not load video source. Exiting.")
        sys.exit(1)

    person_detector = PersonDetector(settings.person_model_path, settings.confidence_threshold)
    pose_detector = PoseDetector(settings.pose_model_path, settings.confidence_threshold)
    fps_counter = FPSCounter()

    logger.info("Initialization complete. Starting main loop.")
    
    frame_count = 0

    try:
        while True:
            success, frame = video_loader.read_frame()
            if not success:
                logger.info("Video ended or cannot read frame.")
                break
                
            frame_count += 1
            
            # FPS Tick
            fps_counter.tick()

            # Detection
            person_detections = person_detector.detect(frame)
            pose_detections = pose_detector.detect(frame)
            
            # Logging count every 60 frames (approx 2s) to avoid spam
            if frame_count % 60 == 0:
                logger.info(f"Frame {frame_count}: Detected {len(person_detections)} person(s), {len(pose_detections)} skeleton(s) | FPS: {fps_counter.get_fps():.1f}")

            # Drawing
            frame = person_detector.draw(frame, person_detections)
            frame = pose_detector.draw(frame, pose_detections)
            frame = fps_counter.draw(frame)

            # Display
            cv2.imshow("Interactive Park AI", frame)

            # Quit on 'q'
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                logger.info("Quit requested by user.")
                break
                
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}")
    finally:
        logger.info("Cleaning up resources...")
        video_loader.release()
        cv2.destroyAllWindows()
        logger.info("Exited.")

if __name__ == "__main__":
    main()
