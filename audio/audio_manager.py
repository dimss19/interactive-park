import logging
import time

class AudioManager:
    """Manages audio triggers based on active zones."""

    def __init__(self):
        # We simulate playing audio for now
        self.playing_left = False
        self.playing_right = False
        
        # Debounce/Cooldown to avoid log spam
        self.last_log_left = 0
        self.last_log_right = 0
        self.log_cooldown = 2.0 # seconds

    def update(self, active_person_zones: list):
        """
        Trigger audio based on where persons are detected.
        """
        current_time = time.time()
        
        # Check Left Zone
        if "LEFT" in active_person_zones:
            if not self.playing_left:
                self.playing_left = True
                logging.info("[AUDIO] -> TRIGGER: ambience_left.mp3 started.")
            elif current_time - self.last_log_left > self.log_cooldown:
                logging.info("[AUDIO] ambience_left.mp3 is playing...")
                self.last_log_left = current_time
        else:
            if self.playing_left:
                self.playing_left = False
                logging.info("[AUDIO] -> STOP: ambience_left.mp3 stopped.")

        # Check Right Zone
        if "RIGHT" in active_person_zones:
            if not self.playing_right:
                self.playing_right = True
                logging.info("[AUDIO] -> TRIGGER: ambience_right.mp3 started.")
            elif current_time - self.last_log_right > self.log_cooldown:
                logging.info("[AUDIO] ambience_right.mp3 is playing...")
                self.last_log_right = current_time
        else:
            if self.playing_right:
                self.playing_right = False
                logging.info("[AUDIO] -> STOP: ambience_right.mp3 stopped.")
