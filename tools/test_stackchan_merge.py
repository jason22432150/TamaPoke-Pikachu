from pathlib import Path
import tempfile
import unittest
import json
from stackchan_merge import assemble,create,verify
from stackchan_package import package
from test_stackchan_review import table,image

class MergeTests(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            bins=root/"bins";bins.mkdir()
            for name in ("TamaPoke.ino.bin","TamaPoke.ino.bootloader.bin"):
                (bins/name).write_bytes(image())
            (bins/"TamaPoke.ino.partitions.bin").write_bytes(table())
            candidate=root/"candidate"
            package(bins,candidate,"a"*40)
            data,report=assemble(candidate)
            self.assertEqual(data[:len(image())],image())
            self.assertEqual(data[0x8000:0x8000+len(table())],table())
            self.assertEqual(data[0x9000:0x20000],b"\xff"*0x17000)
            self.assertEqual(data[0x20000:0x20000+len(image())],image())
            self.assertEqual(len(data)%4096,0)
            self.assertFalse(report["flash_authorized"])
            out=root/"merged"
            self.assertEqual(create(candidate,out),report)
            self.assertEqual(verify(candidate,out),report)
            with self.assertRaises(FileExistsError):
                create(candidate,out)
            merged=out/"merged-review-only.bin"
            merged.write_bytes(data[:-1])
            with self.assertRaises(ValueError):
                verify(candidate,out)
            merged.write_bytes(data)
            m=out/"manifest.json"
            changed=json.loads(m.read_text())
            changed["flash_authorized"]=True
            m.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):
                verify(candidate,out)
            (candidate/"ota_data_initial.bin").write_bytes(b"\0"*8192)
            with self.assertRaises(ValueError):
                assemble(candidate)

if __name__=="__main__":
    unittest.main()
