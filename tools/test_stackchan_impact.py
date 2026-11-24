from pathlib import Path
import tempfile
import unittest
from stackchan_backup import capture
from stackchan_impact import impact,overlaps
from stackchan_package import package
from test_stackchan_review import table,image
from test_stackchan_preflight import runner

class ImpactTests(unittest.TestCase):
    def test_overlap(self):
        self.assertEqual(overlaps(4096,12288,[(0,8192),(12288,16384)]),4096)
    def test_nvs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            factory=root/"factory";current=root/"current"
            capture("fake",factory,runner=runner()[0])
            capture("fake",current,runner=runner(marker=1)[0])
            bins=root/"bins";bins.mkdir()
            for name in ("TamaPoke.ino.bin","TamaPoke.ino.bootloader.bin"):
                (bins/name).write_bytes(image())
            (bins/"TamaPoke.ino.partitions.bin").write_bytes(table())
            candidate=root/"candidate"
            package(bins,candidate,"a"*40)
            result=impact(factory,current,candidate)
            nvs=result["partitions"][0]
            self.assertEqual(nvs["label"],"nvs")
            self.assertTrue(nvs["exact_layout_match"])
            self.assertEqual(nvs["separate_erase_bytes"],0)
            self.assertEqual(nvs["merged_erase_bytes"],0x5000)
            self.assertFalse(result["flash_authorized"])
            self.assertFalse(result["restore_authorized"])
            self.assertIn("merged prefix erases data partition sectors",result["blockers"])
            different=root/"different"
            capture("fake",different,runner=runner(mac="00:11:22:33:44:66")[0])
            with self.assertRaises(ValueError):
                impact(factory,different,candidate)

if __name__=="__main__":
    unittest.main()
