import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
from stackchan_backup import TABLE_BYTES,capture
from stackchan_review import expected_layout,firmware_evidence,review_archive,security_state
from test_stackchan_backup import BackupTests

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

    def test_firmware(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            app=out/"TamaPoke.ino.bin"
            boot=out/"TamaPoke.ino.bootloader.bin"
            part=out/"TamaPoke.ino.partitions.bin"
            app.write_bytes(b"\xe9"+b"\0"*100)
            boot.write_bytes(b"\xe9"+b"\0"*100)
            part.write_bytes(table())
            r=firmware_evidence(out,"a"*40)
            self.assertFalse(r["flash_authorized"])
            self.assertEqual(len(r["files"]),3)
            app.write_bytes(b"\0")
            with self.assertRaises(ValueError):firmware_evidence(out,"a"*40)
            app.write_bytes(b"\xe9")
            part.write_bytes(b"\xff"*TABLE_BYTES)
            with self.assertRaises(ValueError):firmware_evidence(out,"a"*40)

if __name__=="__main__":
    unittest.main()
