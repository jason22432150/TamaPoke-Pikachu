from pathlib import Path
import tempfile
import unittest
from stackchan_package import package,verify_package
from test_stackchan_review import table,image

class PackageTests(unittest.TestCase):
    def test_roundtrip_and_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            bins=root/"bins";bins.mkdir()
            for name in ("TamaPoke.ino.bin","TamaPoke.ino.bootloader.bin"):
                (bins/name).write_bytes(image())
            (bins/"TamaPoke.ino.partitions.bin").write_bytes(table())
            out=root/"candidate"
            m=package(bins,out,"a"*40)
            self.assertEqual(verify_package(out),m)
            self.assertFalse(m["flash_authorized"])
            self.assertFalse(m["factory_compatible"])
            with self.assertRaises(FileExistsError):package(bins,out,"a"*40)
            extra=out/"unexpected.bin";extra.write_bytes(b"x")
            with self.assertRaises(ValueError):verify_package(out)
            extra.unlink()
            (out/"TamaPoke.ino.bin").write_bytes(image(b"wxyz"))
            with self.assertRaises(ValueError):verify_package(out)
    def test_invalid_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaises(ValueError):package(root,root/"candidate","a"*40)
            self.assertFalse((root/"candidate").exists())

if __name__=="__main__":
    unittest.main()
