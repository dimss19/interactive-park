import cv2
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from config.settings import Settings
from utils.logger import setup_logger
from utils.fps_counter import FPSCounter
from input.video_loader import VideoLoader
from pose.pose_detector import PoseDetector
from interaction.area_manager import AreaManager
from interaction.touch_manager import TouchManager
from mapping.area_mapper import AreaMapper
from audio.audio_manager import AudioManager


def wait_until_frame_time(loop_start: float, target_frame_time: float) -> None:
    remaining = target_frame_time - (time.perf_counter() - loop_start)
    if remaining <= 0:
        return
    if remaining > 0.003:
        time.sleep(remaining - 0.002)
    while time.perf_counter() - loop_start < target_frame_time:
        pass


def main():
    logger = setup_logger(log_level=settings.log_level)
    logger.info("Starting Interactive Park AI (Mapping, ROI & Touch Detection)...")

    settings = Settings("config.yaml")
    headless = os.getenv("HEADLESS", "0") == "1"

    video_loader = VideoLoader(settings.video_source)
    if not video_loader.load_video():
        logger.error("Could not load video source. Exiting.")
        sys.exit(1)

    success, first_frame = video_loader.read_frame()
    if not success:
        logger.error("Could not read first frame.")
        sys.exit(1)

    if settings.mapping_enabled and not headless:
        logger.info("Mapping mode started. Press q in the mapping window to start detection.")
        mapper = AreaMapper(settings.config_path)
        mapper.run(first_frame)
        settings.load_config()
    elif settings.mapping_enabled and headless:
        logger.info("Mapping mode skipped because HEADLESS=1.")

    area_manager = AreaManager()
    area_manager.load(settings.areas)

    pose_detector = PoseDetector(
        settings.pose_model_path,
        settings.confidence_threshold,
        imgsz=settings.pose_imgsz,
        device=settings.pose_device,
        half=settings.pose_half,
        use_tracker=settings.use_tracker,
        preprocessing_enabled=settings.preprocessing_enabled,
    )

    logger.info("Warming up pose detector...")
    pose_detector.detect(first_frame)

    audio_manager = AudioManager()
    fps_counter = FPSCounter()
    touch_manager = TouchManager(touch_duration_threshold=0.5, area_manager=area_manager)

    logger.info("Initialization complete. Starting main loop.")

    if isinstance(settings.video_source, str):
        video_loader.reset()

    frame_count = 0
    last_persons = []
    use_async = not settings.use_tracker
    detect_future = None
    detector_executor = ThreadPoolExecutor(max_workers=1) if use_async else None
    target_frame_time = 1.0 / max(settings.target_fps, 1)
    detect_every_n_frames = settings.detect_every_n_frames

    try:
        while True:
            loop_start = time.perf_counter()
            success, frame = video_loader.read_frame()
            if not success:
                logger.info("Video ended or cannot read frame.")
                break

            frame_count += 1

            if use_async:
                if detect_future is not None and detect_future.done():
                    try:
                        last_persons = detect_future.result()
                    except Exception as e:
                        logger.error(f"Pose detection failed: {e}")
                    detect_future = None

                if detect_future is None and (frame_count == 1 or frame_count % detect_every_n_frames == 0):
                    detect_future = detector_executor.submit(pose_detector.detect, frame.copy())
            else:
                if frame_count == 1 or frame_count % detect_every_n_frames == 0:
                    try:
                        last_persons = pose_detector.detect(frame)
                    except Exception as e:
                        logger.error(f"Pose detection failed: {e}")

            persons = last_persons

            active_garden_names = set()
            persons_in_garden = []
            for person in persons:
                garden_area = area_manager.person_in_area_type(person, "garden")
                if garden_area:
                    persons_in_garden.append(person)
                    active_garden_names.add(garden_area["name"])

            audio_manager.update_ambience(active_garden_names)
            touch_events = touch_manager.update(persons_in_garden)
            audio_manager.update_plant_events(touch_events)

            if settings.draw_pose_overlay:
                frame = pose_detector.draw(frame, persons)
            if settings.draw_debug_overlay:
                frame = area_manager.draw(frame)
                frame = area_manager.draw_person_area_status(frame, persons)
            frame = fps_counter.draw(frame)

            if frame_count % max(settings.target_fps, 1) == 0:
                logger.info(
                    f"Frame {frame_count}: Person={len(persons)} | "
                    f"InGarden={len(persons_in_garden)} | DetectEvery={detect_every_n_frames} | FPS={fps_counter.get_fps():.1f}"
                )

            if not headless:
                cv2.imshow("Interactive Park AI", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    logger.info("Quit requested by user.")
                    break
            else:
                if frame_count >= 60:
                    logger.info("Headless testing finished (60 frames).")
                    break

            wait_until_frame_time(loop_start, target_frame_time)
            fps_counter.tick()

    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}")
    finally:
        logger.info("Cleaning up resources...")
        if detector_executor: detector_executor.shutdown(wait=True)
        video_loader.release()
        if not headless:
            cv2.destroyAllWindows()
        logger.info("Exited.")


if __name__ == "__main__":
    main()




