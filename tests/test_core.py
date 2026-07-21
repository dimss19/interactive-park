"""Unit tests for core logic."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import numpy as np
from interaction.area_manager import AreaManager
from interaction.touch_manager import TouchManager
from audio.audio_manager import AudioManager


def make_person(bbox=(0, 0, 100, 200), keypoints_conf=0.8):
    kpts = np.zeros((17, 3))
    kpts[:, 2] = keypoints_conf
    return {"bbox": bbox, "conf": 0.9, "keypoints": kpts}


def make_wrist_person(lw=(50, 180), rw=(70, 180), conf=0.8):
    kpts = np.zeros((17, 3))
    # shoulders
    kpts[5] = [40, 60, conf]
    kpts[6] = [80, 60, conf]
    # hips
    kpts[11] = [45, 140, conf]
    kpts[12] = [75, 140, conf]
    # wrists
    kpts[9] = [*lw, conf]
    kpts[10] = [*rw, conf]
    return {"bbox": (20, 30, 100, 200), "conf": 0.9, "keypoints": kpts}


class FakeChannel:
    def __init__(self):
        self.busy = True
        self.stopped = False

    def get_busy(self):
        return self.busy

    def stop(self):
        self.stopped = True
        self.busy = False


class FakeSound:
    def __init__(self):
        self.play_count = 0
        self.channel = FakeChannel()

    def play(self, loops=0):
        self.play_count += 1
        self.channel.busy = True
        return self.channel


class TestAreaManager:
    def test_load_areas(self):
        am = AreaManager()
        config = {
            "garden": {"name": "Taman", "type": "garden", "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]]},
        }
        am.load(config)
        assert "garden" in am.areas
        assert am.areas["garden"]["name"] == "Taman"

    def test_is_inside(self):
        am = AreaManager()
        am.load({"garden": {"polygon": [[0, 0], [100, 0], [100, 100], [0, 100]]}})
        assert am.is_inside((50, 50), "garden") is True
        assert am.is_inside((200, 200), "garden") is False

    def test_person_center_from_keypoints(self):
        am = AreaManager()
        p = make_person()
        center = am.person_center(p)
        # all keypoints at 0, so centers at (0,0) - but wait, keypoints conf is 0.8 but coords are 0
        # so center should be (0, 0) from keypoints
        assert center is not None

    def test_person_center_fallback_bbox(self):
        am = AreaManager()
        p = make_person()
        p["keypoints"] = np.zeros((0, 3))  # empty keypoints
        center = am.person_center(p)
        assert center == (50, 100)  # center of (0,0)-(100,200)


class TestTouchManager:
    def test_no_persons_no_events(self):
        am = AreaManager()
        am.load({"plant1": {"name": "Plant", "type": "plant", "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]]}})
        tm = TouchManager(0.5, am)
        events = tm.update([])
        assert events == {"touch": [], "release": [], "active": []}

    def test_wrist_in_plant_triggers_active(self):
        am = AreaManager()
        am.load({"plant1": {"name": "Plant", "type": "plant", "polygon": [[0, 0], [200, 0], [200, 200], [0, 200]]}})
        tm = TouchManager(0.01, am)
        p = make_wrist_person(lw=(50, 100), rw=(150, 100))
        events = tm.update([p])
        assert 'Plant' in [am.areas.get(n, {}).get('name', n) for n in events['active']]

    def test_zero_threshold_triggers_touch_immediately(self):
        am = AreaManager()
        am.load({"plant1": {"name": "Plant", "type": "plant", "polygon": [[0, 0], [200, 0], [200, 200], [0, 200]]}})
        tm = TouchManager(0.0, am)
        p = make_wrist_person(lw=(50, 100), rw=(150, 100))
        events = tm.update([p])
        assert events["touch"] == ["Plant"]

    def test_wrist_outside_no_touch(self):
        am = AreaManager()
        am.load({"plant1": {"name": "Plant", "type": "plant", "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]]}})
        tm = TouchManager(0.5, am)
        p = make_wrist_person(lw=(500, 500), rw=(600, 600))
        events = tm.update([p])
        assert events["active"] == []


class TestAudioManager:
    def test_play_skips_same_sfx_while_channel_busy(self):
        audio = AudioManager(enabled=False)
        sound = FakeSound()
        audio.sounds["plant_touch"] = sound

        assert audio.play("plant_touch", loops=0) is True
        assert audio.play("plant_touch", loops=0) is False
        assert sound.play_count == 1

        sound.channel.busy = False
        assert audio.play("plant_touch", loops=0) is True
        assert sound.play_count == 2


if __name__ == "__main__":
    pytest.main([__file__])

