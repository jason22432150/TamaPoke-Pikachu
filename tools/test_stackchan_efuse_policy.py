import subprocess
import tempfile
import unittest
from pathlib import Path

HAL=Path(__file__).resolve().parents[1]/"boards/stackchan/hal"
FLAGS=("CONFIG_SECURE_BOOT","CONFIG_SECURE_BOOT_V2_ENABLED",
       "CONFIG_SECURE_FLASH_ENC_ENABLED","CONFIG_BOOTLOADER_APP_ANTI_ROLLBACK",
       "CONFIG_SECURE_DISABLE_ROM_DL_MODE","CONFIG_SECURE_ENABLE_SECURE_ROM_DL_MODE")

class EfusePolicyTests(unittest.TestCase):
    def compile(self,settings):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"sdkconfig.h").write_text(settings)
            return subprocess.run(["g++","-std=c++11","-fsyntax-only","-x","c++",
                                   "-I",str(root),"-I",str(HAL),"-"],
                                  input='#include "efuse_policy.h"\nint main() {}\n',
                                  text=True,capture_output=True,check=False)
    def test_disabled(self):
        for settings in ("","\n".join("#define "+f+" 0" for f in FLAGS)):
            result=self.compile(settings)
            self.assertEqual(result.returncode,0,result.stderr)
    def test_each_enabled_is_rejected(self):
        for flag in FLAGS:
            with self.subTest(flag=flag):
                result=self.compile("#define "+flag+" 1\n")
                self.assertNotEqual(result.returncode,0)
                self.assertIn("StackChan forbids",result.stderr)

if __name__=="__main__":
    unittest.main()
