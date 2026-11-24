from pathlib import Path
import tempfile
import unittest

from stackchan_backup import capture
from stackchan_preflight import compare_archives,preflight
from test_stackchan_backup import BackupTests

def runner(marker=0,mac="00:11:22:33:44:55",encrypted=False,unknown=False):
    base,calls=BackupTests().make_runner()
    def run(args,path):
        report=base(args,path)
        if "read-mac" in args:report="MAC: "+mac
        elif "get-security-info" in args:
            report="unknown" if unknown else ("Flags: 0x00000000 (0b0)\nSecure Boot: Disabled\nFlash Encryption: "
                +("Enabled" if encrypted else "Disabled")+"\nSPI Boot Crypt Count (SPI_BOOT_CRYPT_CNT): "
                +("0x1" if encrypted else "0x0")+"\n")
        elif "read-flash" in args and marker:
            with Path(args[-1]).open("r+b") as f:
                f.seek(0x9000);f.write(bytes([marker]))
        path.write_text(report)
        return report
    return run,calls

class PreflightTests(unittest.TestCase):
    def test_compare(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);f=root/"factory";c=root/"current"
            capture("fake",f,runner=runner()[0])
            result=preflight(f,c,"fake",runner=runner(marker=1)[0])
            self.assertTrue(result["same_device_mac"])
            self.assertTrue(result["layout_matches"])
            self.assertEqual(result["changed_sectors"],1)
            self.assertEqual(result["factory_partition_changes"][0]["changed_sectors"],1)
            self.assertFalse(result["restore_authorized"])
            self.assertFalse(result["flash_authorized"])
            self.assertEqual(result,compare_archives(f,c))
            with self.assertRaises(ValueError):compare_archives(f,f)
    def test_mismatch_and_security(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);f=root/"factory";c=root/"different";d=root/"security"
            capture("fake",f,runner=runner()[0])
            capture("fake",c,runner=runner(mac="00:11:22:33:44:66")[0])
            with self.assertRaises(ValueError):compare_archives(f,c)
            result=preflight(f,d,"fake",runner=runner(encrypted=True)[0])
            self.assertIn("security state differs",result["blockers"])
            self.assertFalse(result["restore_authorized"])
            u=preflight(f,root/"unknown","fake",runner=runner(unknown=True)[0])
            self.assertIn("current security flags or crypt count unverified",u["blockers"])
    def test_invalid_factory_no_serial(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            run,calls=runner()
            with self.assertRaises(OSError):preflight(root/"missing",root/"current","fake",runner=run)
            self.assertEqual(calls,[])
            self.assertFalse((root/"current").exists())

if __name__=="__main__":
    unittest.main()
