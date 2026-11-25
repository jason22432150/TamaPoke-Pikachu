import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
from stackchan_backup import TABLE_BYTES,capture
from stackchan_review import expected_layout,firmware_evidence,review_archive,security_state,validate_esp_image,initial_ota_data
from test_stackchan_backup import BackupTests

def image(payload=b"abcd", digest=True):
    header=bytearray(24)
    header[0]=0xe9
    header[1]=1
    struct.pack_into("<H",header,12,9)
    header[23]=int(digest)
    raw=bytes(header)+struct.pack("<II",0x40370000,len(payload))+payload
    checksum=0xef
    for v in payload:checksum^=v
    raw=raw.ljust(((len(raw)+16)&~15)-1,b"\0")+bytes([checksum])
    return raw+hashlib.sha256(raw).digest() if digest else raw

def table():
    raw=b"".join(struct.pack("<HBBII16sI",0x50AA,p["type"],p["subtype"],
             p["offset"],p["size"],p["label"].encode(),p["flags"]) for p in expected_layout())
    return (raw+b"\xeb\xeb"+b"\xff"*14+hashlib.md5(raw).digest()).ljust(TABLE_BYTES,b"\xff")

class ReviewTests(unittest.TestCase):
    def test_security(self):
        self.assertEqual(security_state("Secure Boot: Disabled","Secure Boot"),"disabled")
        self.assertEqual(security_state("Secure Boot: Enabled","Secure Boot"),"enabled")
        self.assertEqual(security_state("no result","Secure Boot"),"unknown")
        self.assertEqual(security_state("Secure Boot: Disabled\nSecure Boot: Enabled","Secure Boot"),"unknown")

    def test_review_never_authorizes(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/"archive"
            run,_=BackupTests().make_runner()
            capture("fake",out,runner=run)
            r=review_archive(out)
            self.assertFalse(r["restore_authorized"])
            self.assertFalse(r["flash_authorized"])
            self.assertFalse(r["layout_matches_experimental"])
            self.assertEqual(r["secure_boot"],"unknown")

    def test_partition_image_padding(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            for name in ("TamaPoke.ino.bin","TamaPoke.ino.bootloader.bin"):
                (out/name).write_bytes(image())
            part=out/"TamaPoke.ino.partitions.bin"
            part.write_bytes(table().ljust(0x1000,b"\xff"))
            self.assertEqual(len(firmware_evidence(out,"a"*40)["files"]),3)
            for invalid in (table()+b"\x00", table().ljust(0x1001,b"\xff"), table()[:-1]):
                part.write_bytes(invalid)
                with self.assertRaises(ValueError):
                    firmware_evidence(out,"a"*40)

    def test_esp_image_validation(self):
        good=image()
        validate_esp_image(good)
        validate_esp_image(image(digest=False))
        for offset in (0,1,12,23,28,32,len(good)-33,len(good)-1):
            bad=bytearray(good)
            bad[offset]^=0xff
            with self.assertRaises(ValueError):
                validate_esp_image(bytes(bad))
        for bad in (good[:-1],good+b"x",b"\xe9"):
            with self.assertRaises(ValueError):
                validate_esp_image(bad)

    def test_observed_k151_layout(self):
        # Independent fixture from the real read-only layout report.
        self.assertEqual([(p["label"],p["type"],p["subtype"],p["offset"],p["size"],p["flags"])
                          for p in expected_layout()],[
            ("nvs",1,2,36864,16384,0),
            ("otadata",1,0,53248,8192,0),
            ("phy_init",1,1,61440,4096,0),
            ("ota_0",0,16,131072,5177344,0),
            ("ota_1",0,17,5308416,5177344,0),
            ("assets",1,130,10485760,4194304,0),
            ("coredump",1,3,14680064,65536,0)])
    def test_initial_ota(self):
        data=initial_ota_data()
        self.assertEqual(data,b"\xff"*8192)

    def test_firmware(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            app=out/"TamaPoke.ino.bin"
            boot=out/"TamaPoke.ino.bootloader.bin"
            part=out/"TamaPoke.ino.partitions.bin"
            app.write_bytes(image())
            boot.write_bytes(image())
            part.write_bytes(table())
            r=firmware_evidence(out,"a"*40)
            self.assertFalse(r["flash_authorized"])
            self.assertEqual(len(r["files"]),3)
            app.write_bytes(b"\0")
            with self.assertRaises(ValueError):firmware_evidence(out,"a"*40)
            app.write_bytes(image())
            part.write_bytes(b"\xff"*TABLE_BYTES)
            with self.assertRaises(ValueError):firmware_evidence(out,"a"*40)

if __name__=="__main__":
    unittest.main()
