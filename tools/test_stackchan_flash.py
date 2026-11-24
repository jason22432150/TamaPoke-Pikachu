from pathlib import Path
import tempfile
import hashlib
import json
import unittest
from unittest.mock import patch
from stackchan_flash import install,serial_prefix,probe,identity,after_boot
from test_stackchan_efuse import runner as efuse_runner
from stackchan_deploy_review import plan,check_sdkconfig,efuse_symbol_inventory,rom_write_references,efuse_mmio_literals
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
    def test_simulated_serial_install_and_first_boot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);bins=root/"bins";bins.mkdir()
            for name in ("TamaPoke.ino.bin","TamaPoke.ino.bootloader.bin"):
                (bins/name).write_bytes(image())
            (bins/"TamaPoke.ino.partitions.bin").write_bytes(table())
            c=root/"candidate";package(bins,c,"a"*40)
            p=plan(c);memory={0x8000:table()};commands=[]
            fake_efuse=efuse_runner()
            def serial(args,log):
                commands.append(args)
                self.assertNotIn("--force",args)
                if "--before" in args:
                    self.assertEqual(args[args.index("--before")+1],"no-reset")
                if "get-security-info" in args:
                    report="Secure Boot: Disabled\nFlash Encryption: Disabled"
                elif "flash-id" in args:
                    report="Detected flash size: 16MB"
                elif "write-flash" in args:
                    self.assertIn("no-reset",args)
                    i=args.index("write-flash")+7
                    for offset,name in zip(args[i::2],args[i+1::2]):
                        memory[int(offset,16)]=Path(name).read_bytes()
                    report="simulated write"
                elif "read-flash" in args:
                    offset,size=int(args[-3],16),int(args[-2],16)
                    Path(args[-1]).write_bytes(memory[offset][:size])
                    report="simulated read"
                else:return fake_efuse(args,log)
                log.write_text(report);return report
            out=root/"install"
            with patch("stackchan_flash.APPROVED_BUILDS",frozenset({identity(p)})):
                self.assertEqual(install(c,"/dev/cu.usbmodem1",out,True,serial)["changed_fields"],[])
                self.assertEqual(after_boot("/dev/cu.usbmodem1",out,serial)["status"],"observable-summary-unchanged")
            self.assertEqual(sum("write-flash" in cmd for cmd in commands),1)
            self.assertEqual(sum("read-flash" in cmd for cmd in commands),5)

    def test_readonly_layout_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);bins=root/"bins";bins.mkdir()
            for name in ("TamaPoke.ino.bin","TamaPoke.ino.bootloader.bin"):
                (bins/name).write_bytes(image())
            (bins/"TamaPoke.ino.partitions.bin").write_bytes(table())
            c=root/"candidate";package(bins,c,"a"*40)
            raw=bytearray(table())
            raw[12:15]=b"old"
            terminator=next(i for i in range(0,len(raw),32) if raw[i:i+2]==b"\xeb\xeb")
            raw[terminator+16:terminator+32]=hashlib.md5(raw[:terminator]).digest()
            fake=efuse_runner()
            def serial(args,log):
                self.assertNotIn("write-flash",args)
                if "get-security-info" in args:msg="Secure Boot: Disabled\nFlash Encryption: Disabled"
                elif "flash-id" in args:msg="Detected flash size: 16MB"
                elif "read-flash" in args:
                    Path(args[-1]).write_bytes(raw);msg="simulated read"
                else:return fake(args,log)
                log.write_text(msg);return msg
            out=root/"probe"
            with self.assertRaisesRegex(ValueError,"layout differs"):
                probe(c,"/dev/cu.usbmodem1",out,serial)
            report=json.loads((out/"layout-report.json").read_text())
            self.assertFalse(report["layout_matches"])
            self.assertFalse(report["flash_authorized"])
            self.assertFalse(report["efuse_write_allowed"])
            self.assertNotIn("mac",report)
            self.assertEqual(report["current_partitions"][0]["label"],"old")
            self.assertEqual(report["candidate_partitions"][0]["label"],"nvs")

    def test_port_rejects_argument_injection(self):
        for port in ("@file","--force","/dev/cu.test @file","/tmp/tty"):
            with self.assertRaises(ValueError):serial_prefix(port)
        prefix=serial_prefix("/dev/cu.usbmodem1")
        self.assertEqual(prefix[prefix.index("--before")+1],"no-reset")
        self.assertEqual(prefix[prefix.index("--after")+1],"no-reset")
        self.assertNotIn("--force",serial_prefix("/dev/cu.usbmodem1"))
    def test_efuse_symbol_inventory(self):
        output="app_main T 40000000 10\nesp_efuse_write_field_bit T 40000010 20\n"
        output+="esp_efuse_utility_burn_chip_opt.constprop.0 t 40000030 10\n"
        output+="esp_efuse_read_field_blob T 40000040 10\nets_efuse_program A 40000050\n"
        output+="esp_efuse_set_read_protect U\nesp_efuse_get_key_dis_write T 40000060 10\n"
        report=efuse_symbol_inventory(output,"app_main")
        self.assertEqual(report["linked_code_symbols"],[
            "esp_efuse_utility_burn_chip_opt.constprop.0","esp_efuse_write_field_bit"])
        self.assertEqual(report["absolute_symbols"],["ets_efuse_program"])
        self.assertFalse(report["safety_attested"])
        self.assertEqual(efuse_symbol_inventory("app_main T 40000000 10","app_main")["linked_code_symbols"],[])
        with self.assertRaisesRegex(ValueError,"missing entry"):
            efuse_symbol_inventory("app_main A 40000000","app_main")
    def test_rom_write_references(self):
        nm="ets_efuse_program A 40000050\nets_efuse_write_key A 40000060\n"
        asm="40370000 <app_main>:\n40370000: call8 40000050 <ets_efuse_program>\n40370003: nop\n"
        data=b"prefix"+bytes.fromhex("60000040")+b"suffix"
        result=rom_write_references(nm,asm,data)
        self.assertEqual(result["direct_references"],[
            dict(symbol="ets_efuse_program",instruction_address="40370000")])
        self.assertEqual(result["address_literals"],[
            dict(symbol="ets_efuse_write_key",image_offset=6)])
        result=rom_write_references(nm,"40370000: nop\n",b"no address")
        self.assertEqual(result["direct_references"],[])
        self.assertEqual(result["address_literals"],[])
        with self.assertRaisesRegex(ValueError,"empty ELF disassembly"):
            rom_write_references(nm,"",b"")
    def test_mmio_literals(self):
        data=b"x"+bytes.fromhex("00700060")+bytes.fromhex("d4710060")+bytes.fromhex("44700060")
        report=efuse_mmio_literals(data)
        self.assertEqual(report["register_address_literals"],[
            dict(address="0x60007000",image_offset=1),
            dict(address="0x600071d4",image_offset=5)])
        self.assertFalse(report["safety_attested"])
        self.assertEqual(efuse_mmio_literals(b"no literal")["register_address_literals"],[])
    def test_sdk_duplicate_assignments(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"sdkconfig"
            base='CONFIG_IDF_TARGET="esp32s3"\n'
            p.write_text(base+base+'CONFIG_SECURE_BOOT=n\n# CONFIG_SECURE_BOOT is not set\n')
            self.assertEqual(check_sdkconfig(p)["CONFIG_SECURE_BOOT"],"n")
            for body in ('CONFIG_SECURE_BOOT=y\nCONFIG_SECURE_BOOT=n\n',
                         '# CONFIG_SECURE_BOOT is not set\nCONFIG_SECURE_BOOT=y\n',
                         'CONFIG_SECURE_BOOT=y\n# CONFIG_SECURE_BOOT is not set\n',
                         'CONFIG_IDF_TARGET="esp32"\n'):
                p.write_text(base+body)
                with self.assertRaisesRegex(ValueError,"conflicting SDK setting"):
                    check_sdkconfig(p)
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
