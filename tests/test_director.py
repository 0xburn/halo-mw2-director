import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave

from director.core import ROOT, SOUNDS, SceneError, compile_scene, doctor, read, validate


class DirectorTests(unittest.TestCase):
    def setUp(self):
        self.recipe = read(ROOT / 'director/examples/rust-crossover.scene.json')
        self.scene = compile_scene(self.recipe)

    def test_readable_recipe_preserves_the_accepted_native_take(self):
        self.assertEqual(self.scene, read(ROOT / 'director/templates/rust-crossover.native.json'))
        validate(self.scene)

    def test_unknown_target_is_rejected_before_launch(self):
        self.recipe['actors']['hero']['actions'][1]['target'] = 'typo'
        with self.assertRaisesRegex(SceneError, 'Unknown actor'):
            compile_scene(self.recipe)

    def test_shot_cannot_precede_ads(self):
        self.recipe['actors']['hero']['actions'][1]['at'] = .5
        with self.assertRaisesRegex(SceneError, 'ADS interval'):
            compile_scene(self.recipe)

    def test_duplicate_slots_are_rejected(self):
        self.scene['actors'][1]['id'] = 0
        with self.assertRaisesRegex(SceneError, 'unique contiguous'):
            validate(self.scene)

    def test_slot_limit_is_explicit(self):
        self.scene['actors'].append(copy.deepcopy(self.scene['actors'][-1]))
        with self.assertRaisesRegex(SceneError, '1–16'):
            validate(self.scene)

    def test_reversed_input_window_is_rejected(self):
        self.scene['actors'][0]['buttons'].append([14.08, 14.0, 2])
        with self.assertRaisesRegex(SceneError, 'invalid time interval'):
            validate(self.scene)

    def test_nan_route_and_unsupported_character_are_rejected(self):
        self.scene['actors'][0]['route'][0][1] = float('nan')
        with self.assertRaisesRegex(SceneError, 'finite'):
            validate(self.scene)
        self.scene = compile_scene(self.recipe)
        self.scene['actors'][0]['character'] = 'arbitrary-model'
        with self.assertRaisesRegex(SceneError, 'slot-based'):
            validate(self.scene)

    def test_corrupt_asset_buffers_fail_preflight(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'mp_rust.ff').write_bytes(b'fixture')
            pack = {'positions': [[0, 0, 0]] * 3, 'normals': [[0, 0, 1]] * 3,
                    'uvs': [[0, 0]] * 3, 'joints': [[0, 0, 0, 0]] * 3,
                    'weights': [[1, 0, 0, 0]] * 3, 'indices': [0, 1, 2],
                    'ranges': [[0, 3, 0, 3]],
                    'materials': [{'file': 'texture.rgba', 'width': 1, 'height': 1}]}
            (root / 'texture.rgba').write_bytes(b'\xff' * 4)
            for name in ('chief', 'sniper', 'warthog', 'plasma_grenade', 'rocket_projectile', 'plasma_pistol', 'rocket'):
                (root / f'{name}.json').write_text(json.dumps(pack))
                (root / ('vertices.bin' if name == 'chief' else f'{name}-vertices.bin')).write_bytes(b'\0' * 96)
            for name in SOUNDS:
                with wave.open(str(root / f'{name}.wav'), 'wb') as audio:
                    audio.setparams((1, 2, 22050, 0, 'NONE', 'not compressed'))
                    audio.writeframes(b'\0\0')
            with patch('director.core.PACK', root), patch('director.core.ZONE', root):
                self.assertEqual(doctor(self.scene)['sound_files_checked'], 11)
                (root / 'texture.rgba').write_bytes(b'\0')
                with self.assertRaisesRegex(SceneError, 'RGBA size'):
                    doctor(self.scene)
                (root / 'texture.rgba').write_bytes(b'\xff' * 4)
                (root / 'vertices.bin').write_bytes(b'\0')
                with self.assertRaisesRegex(SceneError, 'vertex data'):
                    doctor(self.scene)


if __name__ == '__main__':
    unittest.main()
