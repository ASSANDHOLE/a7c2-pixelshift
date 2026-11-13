"""Meaningful input and patch-integrity refusal tests; no firmware or device needed."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('offline_builder', ROOT / 'tools/build_offline.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class BuilderTests(unittest.TestCase):
    def test_coefficients_are_explicit_nonzero_integers(self):
        for value in [None, [], [None] * 3, [0, 1, 2], [256, 1, 2], [True, 2, 3], [1.0, 2, 3]]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                builder.coefficients(value)

    def test_round_trip_and_unowned_bytes(self):
        original = b'abcde12345'
        spans = [dict(offset=2, before_hex=b'cd'.hex(), after_hex=b'XY'.hex())]
        patched = builder.transform(original, spans)
        self.assertEqual(patched, b'abXYe12345')
        self.assertEqual(builder.transform(patched, spans, True), original)

    def test_unexpected_input_bytes_refused(self):
        with self.assertRaises(ValueError):
            builder.transform(b'abZdef', [dict(offset=2, before_hex=b'cd'.hex(), after_hex=b'XY'.hex())])

    def test_bad_windows_refused(self):
        for spans in [[dict(offset=-1, before_hex='00', after_hex='01')],
                      [dict(offset=2, before_hex='6364', after_hex='58')],
                      [dict(offset=5, before_hex='6667', after_hex='5859')],
                      [dict(offset=1, before_hex='6263', after_hex='5859'), dict(offset=2, before_hex='6364', after_hex='5859')]]:
            with self.subTest(spans=spans), self.assertRaises(ValueError):
                builder.transform(b'abcdef', spans)

    def test_private_output_cannot_be_public_tree(self):
        for path in [ROOT, ROOT / 'generated']:
            with self.assertRaises(ValueError):
                builder.external_output(path)

    def test_no_existing_output_overwrite(self):
        with tempfile.TemporaryDirectory() as folder, self.assertRaisesRegex(ValueError, 'already exists'):
            builder.build(Path(folder) / 'unused.json', folder)

    def test_wrong_identity_and_missing_parameters_refused_before_output(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            base = dict(schema=1, model='ILCE-7CM2', firmware='2.01', ap_file='absent', cp_file='absent', coefficients=[1, 2, 3])
            for i, change in enumerate([dict(model='ILCE-7CR'), dict(firmware='2.00'), dict(schema=True), dict(ap_file=None), dict(coefficients=[None] * 3), dict(extra=True)]):
                config = folder / 'input.json'; config.write_text(json.dumps(dict(base, **change)))
                output = folder / str(i)
                with self.assertRaises(ValueError):
                    builder.build(config, output)
                self.assertFalse(output.exists())

    def test_wrong_stock_component_refused_before_output(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder); (folder / 'wrong.bin').write_bytes(b'not stock firmware')
            config = folder / 'input.json'
            config.write_text(json.dumps(dict(schema=1, model='ILCE-7CM2', firmware='2.01', ap_file='wrong.bin', cp_file='wrong.bin', coefficients=[1, 2, 3])))
            with self.assertRaisesRegex(ValueError, 'exact stock'):
                builder.build(config, folder / 'output')
            self.assertFalse((folder / 'output').exists())


if __name__ == '__main__':
    unittest.main()
