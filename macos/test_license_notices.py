import unittest
from license_notices import is_notice


class NoticeTests(unittest.TestCase):
    def test_upstream_notice_names(self):
        for name in ('package.dist-info/LICENSE','COPYING.LESSER','NOTICE.txt',
                     'package.dist-info/licenses/Apache-2.0.txt'):
            with self.subTest(name=name):self.assertTrue(is_notice(name,b'License terms'))

    def test_similarly_named_pyobjc_binaries_are_excluded(self):
        for name in ('PyObjCTest/copying.cpython-313-darwin.so',
                     'PyObjCTest/copying.cpython-313-darwin.so.dSYM/Contents/Resources/DWARF/copying.cpython-313-darwin.so'):
            with self.subTest(name=name):self.assertFalse(is_notice(name,b'\xcf\xfa\xed\xfe\x00'))
        self.assertFalse(is_notice('PyObjCTest/copying.cpython-313-darwin.so.dSYM/Contents/Info.plist',b'plist'))
        self.assertFalse(is_notice('package/module.py',b'code'))
