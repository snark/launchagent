import unittest
import pep8
import glob
import os


class TestCodeFormat(unittest.TestCase):

    def test_pep8_conformance(self):
        """Test that we conform to PEP8."""
        localdir = os.path.dirname(os.path.realpath(__file__))
        pep8style = pep8.StyleGuide(quiet=True)
        result = pep8style.check_files(
            glob.glob(os.path.join(localdir, '../launchagent/*.py'))
        )
        self.assertEqual(result.total_errors, 0,
                         "Found code style errors (and warnings) in "
                         "launchagent/.")
        result = pep8style.check_files(
            glob.glob(os.path.join(localdir, './*py'))
        )
        self.assertEqual(result.total_errors, 0,
                         "Found code style errors (and warnings) in tests/.")

if __name__ == '__main__':
    unittest.main()
