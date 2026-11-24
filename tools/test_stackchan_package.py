from pathlib import Path
import tempfile
import hashlib
import json
import struct
import unittest
from stackchan_package import package,verify_package,combine,app_idf_version,IDF_PIN,SOURCE_FILES
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
            ota=out/"ota_data_initial.bin"
            self.assertEqual(ota.read_bytes(),b"\xff"*8192)
            ota.write_bytes(b"\0"+b"\xff"*8191)
            with self.assertRaises(ValueError):verify_package(out)
            ota.write_bytes(b"\xff"*8192)
            extra=out/"unexpected.bin";extra.write_bytes(b"x")
            with self.assertRaises(ValueError):verify_package(out)
            extra.unlink()
            (out/"TamaPoke.ino.bin").write_bytes(image(b"wxyz"))
            with self.assertRaises(ValueError):verify_package(out)
    def test_combine(self):
        def sized_image(payload):
            data=bytearray(image(payload))
            data[2:4]=bytes([2,0x4f])
            data[-32:]=hashlib.sha256(data[:-32]).digest()
            return bytes(data)
        desc=bytearray(256)
        struct.pack_into("<I",desc,0,0xABCD5432)
        desc[112:118]=b"v6.1.1"
        app=sized_image(bytes(desc))
        self.assertEqual(app_idf_version(app),"v6.1.1")
        struct.pack_into("<I",desc,4,1)
        with self.assertRaises(ValueError):app_idf_version(sized_image(desc))
        struct.pack_into("<I",desc,4,0)
        desc[112:118]=b"v5.5.0"
        with self.assertRaises(ValueError):app_idf_version(sized_image(desc))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);bins=root/"bins";bins.mkdir()
            old_boot=sized_image(b"old!")
            new_boot=sized_image(b"new!")
            (bins/"TamaPoke.ino.bin").write_bytes(app)
            (bins/"TamaPoke.ino.bootloader.bin").write_bytes(old_boot)
            (bins/"TamaPoke.ino.partitions.bin").write_bytes(table())
            candidate=root/"candidate";package(bins,candidate,"a"*40)
            src=root/"source";src.mkdir()
            for name in SOURCE_FILES:
                (src/name).write_bytes(new_boot if name=="bootloader.bin" else b"fixture")
            (src/"READ-ME-NOT-FOR-FLASH.txt").write_text("NOT FOR FLASH")
            digest=lambda b:hashlib.sha256(b).hexdigest()
            m=dict(schema=1,kind="source-bootloader-reference",idf_version="6.1.1",
                   idf_commit=IDF_PIN,source_commit="a"*40,flash_authorized=False,
                   bootloader_security_attested=False,
                   files={n:digest((src/n).read_bytes()) for n in SOURCE_FILES})
            manifest=src/"manifest.json";manifest.write_text(json.dumps(m))
            evidence=root/"arduino.json"
            evidence.write_text(json.dumps(dict(source_commit="a"*40,arduino_core="4.0.0",
                elf_conversion_matches=True,flash_authorized=False,bootloader_security_attested=False,
                app_sha256=digest(app),bootloader_bin_sha256=digest(old_boot))))
            out=root/"paired"
            report=combine(candidate,src,evidence,out)
            self.assertFalse(report["flash_authorized"])
            self.assertEqual((out/"TamaPoke.ino.bootloader.bin").read_bytes(),new_boot)
            self.assertEqual((out/"TamaPoke.ino.bin").read_bytes(),app)
            self.assertEqual(report["paired_manifest"],verify_package(out))
            m["source_commit"]="b"*40;manifest.write_text(json.dumps(m))
            with self.assertRaises(ValueError):combine(candidate,src,evidence,root/"bad")
            m["source_commit"]="a"*40;manifest.write_text(json.dumps(m))
            (src/"bootloader.bin").write_bytes(old_boot)
            with self.assertRaises(ValueError):combine(candidate,src,evidence,root/"bad")
    def test_invalid_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaises(ValueError):package(root,root/"candidate","a"*40)
            self.assertFalse((root/"candidate").exists())

if __name__=="__main__":
    unittest.main()
