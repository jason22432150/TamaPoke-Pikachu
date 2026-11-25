import unittest
from stackchan_assets import build_image,verify_image,IDS,SIZE,START,source_assets

class AssetsTests(unittest.TestCase):
    def test_real_pack(self):
        items=source_assets()
        image=build_image(items)
        report=verify_image(image)
        self.assertEqual(len(image),SIZE)
        self.assertEqual(len(report["files"]),23)
        self.assertEqual(report["used_bytes"],START+sum(map(len,items.values())))
        self.assertEqual(build_image(items),image)
    def test_corruption(self):
        items={i:(b"TPK2abc" if i else b"TPTHabcdef") for i in IDS}
        good=build_image(items)
        for offset in (0,16,START,SIZE-1):
            bad=bytearray(good);bad[offset]^=1
            with self.assertRaises(ValueError):verify_image(bytes(bad))
        with self.assertRaises(ValueError):verify_image(good[:-1])
        del items[0]
        with self.assertRaises(ValueError):build_image(items)

if __name__=="__main__":unittest.main()
