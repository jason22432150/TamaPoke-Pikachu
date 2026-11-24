from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from stackchan_flash import install,serial_prefix,probe,identity
from stackchan_deploy_review import plan,check_sdkconfig
from stackchan_package import package
from test_stackchan_review import image,table

class FlashTests(unittest.TestCase):
    def test_unapproved_never_opens_serial(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);bins=root/"bins";bins.mkdir()
            for name in ("TamaPoke.ino.bin","TamaPoke.ino.bootloader.bin"):
                (bins/name).write_bytes(image())
            (bins/"TamaPoke.ino.partitions.bin").write_bytes(table())
            c=root/"candidate";package(bins,c,"a"*40)
            def never(*args,**kwargs):raise AssertionError("unexpected device access")
            with self.assertRaisesRegex(ValueError,"NOT FOR FLASH"):
                install(c,"/dev/cu.usbmodem1",root/"out",True,never,never)
            self.assertFalse((root/"out").exists())
            with patch("stackchan_flash.APPROVED_BUILDS",frozenset({identity(plan(c))})):
                with self.assertRaisesRegex(ValueError,"acknowledgement"):
                    install(c,"/dev/cu.usbmodem1",root/"out",False,never,never)
                with self.assertRaises(ValueError):
                    probe(c,"@arguments",root/"out",never,never)
    def test_port_rejects_argument_injection(self):
        for port in ("@file","--force","/dev/cu.test @file","/tmp/tty"):
            with self.assertRaises(ValueError):serial_prefix(port)
        self.assertIn("no-reset",serial_prefix("/dev/cu.usbmodem1"))
        self.assertNotIn("--force",serial_prefix("/dev/cu.usbmodem1"))
    def test_sdk_security(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"sdkconfig"
            p.write_text('CONFIG_IDF_TARGET="esp32s3"\n')
            self.assertEqual(check_sdkconfig(p)["CONFIG_SECURE_BOOT"],"not-defined")
            for setting in ("CONFIG_SECURE_BOOT","CONFIG_SECURE_FLASH_ENC_ENABLED",
                            "CONFIG_BOOTLOADER_APP_ANTI_ROLLBACK","CONFIG_SECURE_DISABLE_ROM_DL_MODE"):
                p.write_text('CONFIG_IDF_TARGET="esp32s3"\n'+setting+'=y\n')
                with self.assertRaises(ValueError):check_sdkconfig(p)
            p.write_text('CONFIG_IDF_TARGET="esp32"\n')
            with self.assertRaises(ValueError):check_sdkconfig(p)

if __name__=="__main__":unittest.main()
