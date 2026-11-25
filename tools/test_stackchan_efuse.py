import json
from pathlib import Path
import tempfile
import unittest
from stackchan_efuse import capture,verify,compare,REQUIRED,raw_crypt_count,checked_crypt_count

def runner(changed=False,mac="00:11:22:33:44:55",missing=False,mac_status=" (OK)",crypt_count=0):
    def run(args,path):
        if args[-1]=="version":
            report="esptool v5.1.0"
        elif args[-1]=="read-mac":
            assert "--no-stub" in args
            report="MAC: "+mac
        elif args[-1]=="get-security-info":
            assert "--no-stub" in args
            report=f"SPI Boot Crypt Count (SPI_BOOT_CRYPT_CNT): {crypt_count:#x}"
        elif "summary" in args:
            assert args[1:3]==["-m","espefuse"]
            assert args[-4:-1]==["--format","json","--file"]
            data={k:dict(name=k,value=0,readable=True,writeable=True,
                         block=0,word=0,pos=0,bit_len=1,efuse_type="uint:1") for k in REQUIRED}
            data["MAC"]["value"]=mac+mac_status
            data["WR_DIS"]["value"]=int(changed)
            data["SPI_BOOT_CRYPT_CNT"]["value"]={0:"Disable",1:"Enable",3:"Disable",7:"Enable"}.get(crypt_count,crypt_count)
            if missing:del data["RD_DIS"]
            Path(args[-1]).write_text(json.dumps(data))
            report="summary complete"
        else:raise AssertionError("unexpected command")
        path.write_text(report)
        return report
    return run

class SnapshotTests(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);a=root/"a";b=root/"b";c=root/"c";d=root/"d"
            self.assertEqual(capture("fake",a,runner()),verify(a))
            capture("fake",b,runner())
            self.assertEqual(compare(a,b)["changed_fields"],[])
            capture("fake",c,runner(changed=True))
            self.assertEqual(compare(a,c)["changed_fields"],["WR_DIS"])
            capture("fake",d,runner(mac="00:11:22:33:44:66"))
            with self.assertRaises(ValueError):compare(a,d)
            with self.assertRaises(ValueError):compare(a,a)
            with (b/"summary.json").open("a") as f:f.write(" ")
            with self.assertRaises(ValueError):verify(b)
            with self.assertRaises(FileExistsError):capture("fake",a,runner())
    def test_real_mac_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            self.assertEqual(capture("fake",root/"ok",runner())["mac"],"00:11:22:33:44:55")
            self.assertEqual(capture("fake",root/"legacy",runner(mac_status=""))["mac"],"00:11:22:33:44:55")
            for i,status in enumerate((" (Block1 has ERRORS:1 FAIL:True)"," (UNKNOWN)"," extra")):
                out=root/str(i)
                with self.assertRaisesRegex(ValueError,"summary MAC"):
                    capture("fake",out,runner(mac_status=status))
                self.assertFalse((out/"manifest.json").exists())
    def test_raw_count(self):
        prefix="SPI Boot Crypt Count (SPI_BOOT_CRYPT_CNT): "
        for raw in range(8):
            report=prefix+hex(raw)
            meaning={0:"Disable",1:"Enable",3:"Disable",7:"Enable"}.get(raw,raw)
            self.assertEqual(checked_crypt_count(dict(readable=True,value=meaning),report),raw)
            self.assertEqual(checked_crypt_count(dict(readable=True,value=raw),report),raw)
        for report in ("",prefix+"0x8",prefix+"0x0\n"+prefix+"0x0",prefix+"unknown"):
            with self.assertRaises(ValueError):raw_crypt_count(report)
        for row in (dict(readable=False,value="Disable"),dict(readable=True,value="Enable"),
                    dict(readable=True,value=False),dict(readable=True,value=3)):
            with self.assertRaises(ValueError):checked_crypt_count(row,prefix+"0x0")
    def test_raw_count_change_even_when_meaning_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=Path(tmp)/"a",Path(tmp)/"b"
            capture("fake",a,runner(crypt_count=0))
            capture("fake",b,runner(crypt_count=3))
            self.assertEqual(compare(a,b)["changed_fields"],["SPI_BOOT_CRYPT_CNT"])
    def test_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/"bad"
            with self.assertRaises(ValueError):capture("fake",out,runner(missing=True))
            self.assertFalse((out/"manifest.json").exists())

if __name__=="__main__":unittest.main()
