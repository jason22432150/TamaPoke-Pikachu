import json
from pathlib import Path
import tempfile
import unittest
from stackchan_efuse import capture,verify,compare,REQUIRED

def runner(changed=False,mac="00:11:22:33:44:55",missing=False):
    def run(args,path):
        if args[-1]=="version":
            report="esptool v5.1.0"
        elif args[-1]=="read-mac":
            report="MAC: "+mac
        elif "summary" in args:
            assert args[1:3]==["-m","espefuse"]
            assert args[-4:-1]==["--format","json","--file"]
            data={k:dict(name=k,value=0,readable=True,writeable=True,
                         block=0,word=0,pos=0,bit_len=1,efuse_type="uint:1") for k in REQUIRED}
            data["MAC"]["value"]=mac
            data["WR_DIS"]["value"]=int(changed)
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
    def test_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/"bad"
            with self.assertRaises(ValueError):capture("fake",out,runner(missing=True))
            self.assertFalse((out/"manifest.json").exists())

if __name__=="__main__":unittest.main()
