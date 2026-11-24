from pathlib import Path
import tempfile
import unittest
import shutil
from stackchan_deploy_review import plan,readback,checkpoints,mmio_instruction_window
from stackchan_package import package
from stackchan_efuse import capture
from test_stackchan_review import image,table
from test_stackchan_efuse import runner

class DeploymentTests(unittest.TestCase):
    def test_plan_and_readback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);bins=root/"bins";bins.mkdir()
            for name in ("TamaPoke.ino.bin","TamaPoke.ino.bootloader.bin"):
                (bins/name).write_bytes(image())
            (bins/"TamaPoke.ino.partitions.bin").write_bytes(table())
            candidate=root/"candidate"
            package(bins,candidate,"a"*40)
            p=plan(candidate)
            self.assertFalse(p["flash_authorized"])
            self.assertFalse(p["efuse_write_allowed"])
            self.assertEqual([r["offset"] for r in p["regions"]],[0,0x8000,0xe000,0x10000])
            self.assertEqual(p["regions"][1]["erase_end"],0x9000)
            self.assertEqual(p["regions"][2]["erase_end"],0x10000)
            out=root/"readback";out.mkdir()
            for r in p["regions"]:shutil.copyfile(candidate/r["name"],out/r["name"])
            self.assertEqual(readback(candidate,out)["status"],"supplied-readback-matches")
            f=out/"TamaPoke.ino.bin"
            original=f.read_bytes()
            f.write_bytes(bytes([original[0]^1])+original[1:])
            with self.assertRaises(ValueError):readback(candidate,out)
            f.write_bytes(original[:-1])
            with self.assertRaises(ValueError):readback(candidate,out)
            f.write_bytes(original)
            (out/"extra").touch()
            with self.assertRaises(ValueError):readback(candidate,out)
    def test_checkpoints(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b,c,d,e=[Path(tmp)/n for n in "abcde"]
            for p in (a,b,c):capture("fake",p,runner())
            capture("fake",d,runner(changed=True))
            capture("fake",e,runner(mac="00:11:22:33:44:66"))
            self.assertEqual(checkpoints(a,b,c)["status"],"observable-summary-unchanged")
            self.assertEqual(checkpoints(a,b,d)["status"],"changed")
            self.assertEqual(checkpoints(a,d,c)["after_write"]["changed_fields"],["WR_DIS"])
            with self.assertRaises(ValueError):checkpoints(a,a,c)
            with self.assertRaises(ValueError):checkpoints(a,b,e)

    def test_mmio_instruction_window(self):
        disassembly = "\n".join([
            "40000000: l32r a2, 40001000",
            "40000003: l32i a3, a2, 0",
            "40000006: beqz a3, 40000010",
            "40000009: s32i a3, a2, 4",
        ])
        self.assertEqual(mmio_instruction_window(disassembly, "40000000"),
                         ["40000003: l32i a3, a2, 0",
                          "40000006: beqz a3, 40000010"])
        self.assertEqual(mmio_instruction_window(disassembly, "40000000", limit=1),
                         ["40000003: l32i a3, a2, 0"])
        self.assertEqual(mmio_instruction_window(disassembly, "40000001"), [])
        boundary = "40000000: l32r a2, 40001000\n40000003 <next>:\n40000003: ret"
        self.assertEqual(mmio_instruction_window(boundary, "40000000"), [])

if __name__=="__main__":unittest.main()
