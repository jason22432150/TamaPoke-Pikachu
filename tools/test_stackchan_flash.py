from pathlib import Path
import tempfile
import sys
import types
import hashlib
import json
import unittest
import subprocess
from stackchan_flash import TransferProgress, run_transfer_logged
from unittest.mock import patch
from stackchan_flash import install,serial_prefix,probe,identity,after_boot,rom_write_command,ROM_WRITE_LAUNCHER,require_approved,APPROVED_BUILDS,CHECKPOINT_BUILDS
from test_stackchan_efuse import runner as efuse_runner
from stackchan_deploy_review import plan,check_sdkconfig,efuse_symbol_inventory,rom_write_references,efuse_mmio_literals,mmio_literal_context
from stackchan_package import package
from test_stackchan_review import image,table

class FlashTests(unittest.TestCase):
    def test_transfer_progress_partial_records(self):
        lines=[]
        p=TransferProgress(lines.append)
        p.feed(b"MAC: private\rWriting at 0x00000000 [    ]  0.")
        p.feed(b"0% 0/100 bytes...\rWriting at 0x00000020 [==> ] 50.0%\n")
        p.feed(b"Writing at 0x00000021 [==> ] 51.0%\rWriting at 0x00000040 [====] 100.0%")
        p.finish()
        self.assertEqual(len(lines),3)
        self.assertIn("0.0%",lines[0])
        self.assertIn("50.0%",lines[1])
        self.assertIn("100.0%",lines[2])
        p.feed(b"\rReading from 0x00008000 [====] 100.0%\n")
        self.assertIn("Reading from",lines[-1])
        self.assertNotIn("private"," ".join(lines))

    def test_transfer_runner_logs_and_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);lines=[]
            code="print('Writing at 0x00000000 [====] 100.0%'); print('private')"
            args=[sys.executable,"-c",code,"write-flash"]
            log=root/"write.log"
            self.assertIn("private",run_transfer_logged(args,log,emit=lines.append))
            self.assertEqual(len(lines),1)
            self.assertNotIn("private",lines[0])
            with self.assertRaises(FileExistsError):
                run_transfer_logged(args,log,emit=lines.append)
            with self.assertRaisesRegex(RuntimeError,"command failed"):
                run_transfer_logged([sys.executable,"-c",code+"; raise SystemExit(1)","write-flash"],
                                    root/"failed.log",emit=lines.append)
            with self.assertRaises(subprocess.TimeoutExpired):
                run_transfer_logged([sys.executable,"-c","import time; time.sleep(5)","read-flash"],
                                    root/"timeout.log",emit=lines.append,timeout=0.1)

    def test_failed_boot_candidate_is_withdrawn(self):
        approved=(
            "bb5234ef25ca5903309028b76afcbc29dc414011",
            "8a7d2bb8a3ea22e1b8d9d44c2ec0e965727231066feda335234a16ac8ea0de0a",
            "d0d54b1feab01787a8b36f606b00f29ede2f4375d5b8b1c48577a83b8644ed2b",
            "48da0866f56d9d8eb1fe786412984d8f1a4a01b3f13f965621fcb916761e1a4b",
            "7d2c7ac4888bfd75cd5f56e8d61f69595121183afc81556c876732fd3782c62f",
        )
        fixed=(
            "871e6d8851c6b7348bbf5a0d71a80affa10e1e32",
            "2b96dbdd514a69af17c2d6425de8cc10939051e3a03462ae4a2c6ffc1249f512",
            "504181669538c9de2b8a866fb62ff5e44ec8cb6c744dfd9127fedf5a9270e05b",
            "48da0866f56d9d8eb1fe786412984d8f1a4a01b3f13f965621fcb916761e1a4b",
            "7d2c7ac4888bfd75cd5f56e8d61f69595121183afc81556c876732fd3782c62f",
        )
        landscape=(
            "01266e011f68e7e4c78c093efb0d4f882b70ee45",
            "f544e71912a4ef440c8f428ac6fd1b5cc1cb1c5bd3b6a007cf267f0dea5fb648",
            "379d3e349cb0d8cfc5cec0b9014d7ed387558530ade8e4a034a1f0d82d9c554a",
            "48da0866f56d9d8eb1fe786412984d8f1a4a01b3f13f965621fcb916761e1a4b",
            "7d2c7ac4888bfd75cd5f56e8d61f69595121183afc81556c876732fd3782c62f",
        )
        interaction=(
            "a3e4428e7f82ed450450a45c8550dc701de4e48b",
            "35c75da84b1221eaa0e345b0229ff2f4bbcc11e31d17150747f13c223c47e9cb",
            "ae2c6b9bfd38a5ef2c74b5ca62fefd94876297e2d9e4080c3ae4e26eed7d9312",
            "48da0866f56d9d8eb1fe786412984d8f1a4a01b3f13f965621fcb916761e1a4b",
            "7d2c7ac4888bfd75cd5f56e8d61f69595121183afc81556c876732fd3782c62f",
        )
        fps=(
            "54d9a27d2e735ba8b051aaa44aed9de79096a97b",
            "0a33b61168e1e18b4bd846aa833a85326a321e67ec6dc0a92342d3ec8b61976f",
            "273f5a4bc7098b2c11b231f31c54a717cd68d1f8d866ea3c62ae0eae220ba707",
            "48da0866f56d9d8eb1fe786412984d8f1a4a01b3f13f965621fcb916761e1a4b",
            "7d2c7ac4888bfd75cd5f56e8d61f69595121183afc81556c876732fd3782c62f",
        )
        optimized=(
            "0bb39e5292d712007612b248ac005dac1bfc558b",
            "eb607f98fd500ebaeb5c6da9649d98458e8f8601a5e6a2525c25e694c8cdfc91",
            "8ac9ac7aea76f77f0bfb21e6563b70abef424ee535b43f3ab169eb52c154e707",
            "48da0866f56d9d8eb1fe786412984d8f1a4a01b3f13f965621fcb916761e1a4b",
            "7d2c7ac4888bfd75cd5f56e8d61f69595121183afc81556c876732fd3782c62f",
        )
        standalone=(
            "e21c476b278544793f9ecd56ff770c0f30cae1f8",
            "6de5b257f7d66b1662fd5db3eb836508675e89f575883c420842ceebf82696f1",
            "b9d4470ee0c4ac7053a8b6ff388e1760db76bc51bbf8efbbd2b2f4f853e9a54a",
            "48da0866f56d9d8eb1fe786412984d8f1a4a01b3f13f965621fcb916761e1a4b",
            "7d2c7ac4888bfd75cd5f56e8d61f69595121183afc81556c876732fd3782c62f",
        )
        coldboot=(
            "d830ac15cc1761aa421b33035ccfa0bb5f93fd1c",
            "89a958cdeb364677fb217072750fe3b6c2c7ca00e6bf8d5fb6398ff2696316d8",
            "4a8a63d4166d8d058389cc469519c6f0ccae315a6939cadaae64e6c7f0532ea5",
            "48da0866f56d9d8eb1fe786412984d8f1a4a01b3f13f965621fcb916761e1a4b",
            "7d2c7ac4888bfd75cd5f56e8d61f69595121183afc81556c876732fd3782c62f",
        )
        traced=(
            "6d1b2183e6717bcde9b905178826a0f06d6bd584",
            "225c3addcce44aea056a1f37c2497cf69c157f0c5ab95c0409bd6a9e253fae19",
            "d7eb8ad05252e5d7be92ae62d2150c0f3abaefa82371c39b6afd523b6cc2f4ad",
            "48da0866f56d9d8eb1fe786412984d8f1a4a01b3f13f965621fcb916761e1a4b",
            "7d2c7ac4888bfd75cd5f56e8d61f69595121183afc81556c876732fd3782c62f",
        )
        self.assertEqual(APPROVED_BUILDS,frozenset({fixed,landscape,interaction,fps,optimized,standalone,traced}))
        self.assertEqual(CHECKPOINT_BUILDS,frozenset({approved,coldboot}))
        names=("TamaPoke.ino.bootloader.bin","TamaPoke.ino.bin",
               "TamaPoke.ino.partitions.bin","ota_data_initial.bin")
        def as_plan(t):
            return dict(source_commit=t[0],regions=[
                dict(name=n,sha256=h) for n,h in zip(names,t[1:])])
        with self.assertRaisesRegex(ValueError,"NOT FOR FLASH"):
            require_approved(as_plan(approved))
        with self.assertRaisesRegex(ValueError,"NOT FOR FLASH"):
            require_approved(as_plan(coldboot))
        for candidate in (fixed,landscape,interaction,fps,optimized,standalone,traced):
            require_approved(as_plan(candidate))
            for i in range(len(candidate)):
                tampered=list(candidate)
                tampered[i]="0"*len(tampered[i])
                with self.assertRaisesRegex(ValueError,"NOT FOR FLASH"):
                    require_approved(as_plan(tampered))
        with self.assertRaisesRegex(ValueError,"NOT FOR FLASH"):
            require_approved(as_plan((landscape[0],fixed[1],*landscape[2:])))
        with self.assertRaisesRegex(ValueError,"NOT FOR FLASH"):
            require_approved(as_plan((interaction[0],landscape[1],*interaction[2:])))
        with self.assertRaisesRegex(ValueError,"NOT FOR FLASH"):
            require_approved(as_plan((fps[0],interaction[1],*fps[2:])))
        with self.assertRaisesRegex(ValueError,"NOT FOR FLASH"):
            require_approved(as_plan((fps[0],fps[1],interaction[2],*fps[3:])))
        with self.assertRaisesRegex(ValueError,"NOT FOR FLASH"):
            require_approved(as_plan((optimized[0],fps[1],*optimized[2:])))
        with self.assertRaisesRegex(ValueError,"NOT FOR FLASH"):
            require_approved(as_plan((optimized[0],optimized[1],fps[2],*optimized[3:])))
        with self.assertRaisesRegex(ValueError,"NOT FOR FLASH"):
            require_approved(as_plan((fps[0],optimized[1],*fps[2:])))
        with self.assertRaisesRegex(ValueError,"NOT FOR FLASH"):
            require_approved(as_plan((standalone[0],optimized[1],*standalone[2:])))
        with self.assertRaisesRegex(ValueError,"NOT FOR FLASH"):
            require_approved(as_plan((standalone[0],standalone[1],optimized[2],*standalone[3:])))
        with self.assertRaisesRegex(ValueError,"NOT FOR FLASH"):
            require_approved(as_plan((optimized[0],standalone[1],*optimized[2:])))
        with self.assertRaisesRegex(ValueError,"NOT FOR FLASH"):
            require_approved(as_plan((coldboot[0],standalone[1],*coldboot[2:])))
        with self.assertRaisesRegex(ValueError,"NOT FOR FLASH"):
            require_approved(as_plan((coldboot[0],coldboot[1],standalone[2],*coldboot[3:])))
        with self.assertRaisesRegex(ValueError,"NOT FOR FLASH"):
            require_approved(as_plan((standalone[0],coldboot[1],*standalone[2:])))
        with self.assertRaisesRegex(ValueError,"NOT FOR FLASH"):
            require_approved(as_plan((traced[0],coldboot[1],*traced[2:])))
        with self.assertRaisesRegex(ValueError,"NOT FOR FLASH"):
            require_approved(as_plan((traced[0],traced[1],coldboot[2],*traced[3:])))
        with self.assertRaisesRegex(ValueError,"NOT FOR FLASH"):
            require_approved(as_plan((coldboot[0],*traced[1:])))
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
                    report="Secure Boot: Disabled\nFlash Encryption: Disabled\nSPI Boot Crypt Count (SPI_BOOT_CRYPT_CNT): 0x0"
                elif "flash-id" in args:
                    report="Detected flash size: 16MB"
                elif "write-flash" in args:
                    self.assertIn("no-reset",args)
                    self.assertIn("--no-stub",args)
                    self.assertEqual(args[1:3],["-c",ROM_WRITE_LAUNCHER])
                    i=args.index("write-flash")+7
                    self.assertEqual([int(x,16) for x in args[i::2]],[0,0xd000,0x20000])
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
                stages=[]
                self.assertEqual(install(c,"/dev/cu.usbmodem1",out,True,serial,progress=stages.append)["changed_fields"],[])
                self.assertEqual(len(stages),6)
                self.assertTrue(stages[-1].startswith("100%"))
                self.assertEqual(after_boot("/dev/cu.usbmodem1",out,serial)["status"],"observable-summary-unchanged")
            self.assertEqual(sum("write-flash" in cmd for cmd in commands),1)
            self.assertEqual(sum("read-flash" in cmd for cmd in commands),6)

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
                if "get-security-info" in args:msg="Secure Boot: Disabled\nFlash Encryption: Disabled\nSPI Boot Crypt Count (SPI_BOOT_CRYPT_CNT): 0x0"
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
            self.assertFalse(report["table_bytes_match"])
            self.assertFalse(report["flash_authorized"])
            self.assertFalse(report["efuse_write_allowed"])
            self.assertNotIn("mac",report)
            self.assertEqual(report["current_partitions"][0]["label"],"old")
            self.assertEqual(report["candidate_partitions"][0]["label"],"nvs")

    def test_probe_rejects_equal_layout_different_table_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);bins=root/"bins";bins.mkdir()
            for name in ("TamaPoke.ino.bin","TamaPoke.ino.bootloader.bin"):
                (bins/name).write_bytes(image())
            (bins/"TamaPoke.ino.partitions.bin").write_bytes(table())
            c=root/"candidate";package(bins,c,"a"*40)
            raw=bytearray(table())
            # Change unused bytes after the first NUL in the NVS label;
            # parsed entries remain identical and the MD5 is recomputed.
            raw[16]=0x58
            terminator=next(i for i in range(0,len(raw),32) if raw[i:i+2]==b"\xeb\xeb")
            raw[terminator+16:terminator+32]=hashlib.md5(raw[:terminator]).digest()
            fake=efuse_runner()
            def serial(args,log):
                self.assertNotIn("write-flash",args)
                if "get-security-info" in args:
                    msg="Secure Boot: Disabled\nFlash Encryption: Disabled\nSPI Boot Crypt Count (SPI_BOOT_CRYPT_CNT): 0x0"
                elif "flash-id" in args:msg="Detected flash size: 16MB"
                elif "read-flash" in args:
                    Path(args[-1]).write_bytes(raw);msg="simulated read"
                else:return fake(args,log)
                log.write_text(msg);return msg
            out=root/"probe"
            with self.assertRaisesRegex(ValueError,"partition table bytes differ"):
                probe(c,"/dev/cu.usbmodem1",out,serial)
            report=json.loads((out/"layout-report.json").read_text())
            self.assertTrue(report["layout_matches"])
            self.assertFalse(report["table_bytes_match"])
            self.assertFalse(report["flash_authorized"])

    def test_probe_rejects_nonzero_raw_count_even_when_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);bins=root/"bins";bins.mkdir()
            for name in ("TamaPoke.ino.bin","TamaPoke.ino.bootloader.bin"):
                (bins/name).write_bytes(image())
            (bins/"TamaPoke.ino.partitions.bin").write_bytes(table())
            c=root/"candidate";package(bins,c,"a"*40)
            fake=efuse_runner(crypt_count=3)
            def serial(args,log):
                self.assertNotIn("write-flash",args)
                self.assertNotIn("read-flash",args)
                if "get-security-info" in args:
                    report="Secure Boot: Disabled\nFlash Encryption: Disabled\nSPI Boot Crypt Count (SPI_BOOT_CRYPT_CNT): 0x3"
                    log.write_text(report)
                    return report
                return fake(args,log)
            with self.assertRaisesRegex(ValueError,"raw count must be zero"):
                probe(c,"/dev/cu.usbmodem1",root/"probe",serial)
    def test_port_rejects_argument_injection(self):
        for port in ("@file","--force","/dev/cu.test @file","/tmp/tty"):
            with self.assertRaises(ValueError):serial_prefix(port)
        prefix=serial_prefix("/dev/cu.usbmodem1")
        self.assertEqual(prefix[prefix.index("--before")+1],"no-reset")
        self.assertEqual(prefix[prefix.index("--after")+1],"no-reset")
        self.assertNotIn("--force",serial_prefix("/dev/cu.usbmodem1"))
        self.assertIn("--no-stub",prefix)
        self.assertEqual(rom_write_command("/dev/cu.usbmodem1")[3:],prefix[3:])
    def test_rom_write_launcher_disables_reconnect(self):
        class ROM:
            WRITE_FLASH_ATTEMPTS=2
        module=types.ModuleType("esptool")
        module.__version__="5.1.0"
        calls=[]
        module.main=lambda: calls.append(ROM.WRITE_FLASH_ATTEMPTS)
        target=types.ModuleType("esptool.targets.esp32s3")
        target.ESP32S3ROM=ROM
        with patch.dict(sys.modules,{"esptool":module,"esptool.targets":types.ModuleType("esptool.targets"),"esptool.targets.esp32s3":target}):
            exec(ROM_WRITE_LAUNCHER,{})
            self.assertEqual(calls,[1])
            module.__version__="5.1.1"
            with self.assertRaises(SystemExit):exec(ROM_WRITE_LAUNCHER,{})
            self.assertEqual(calls,[1])
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
    def test_mmio_literal_context(self):
        import struct
        header=bytearray(24)
        header[0]=0xe9
        header[1]=2
        data=bytes(header)+struct.pack("<II",0x40370000,8)+b"abcd"+struct.pack("<I",0x60007000)
        data+=struct.pack("<II",0x42000000,4)+struct.pack("<I",0x60007000)
        hits=[dict(image_offset=36),dict(image_offset=48),dict(image_offset=20)]
        asm=("40370100: l32r a8, 40370004 <literal>\n"
             "40370103: l32r a9, 0x42000000 <literal2>\n"
             "40370106: l32r a8, 403700040 <different>\n")
        result=mmio_literal_context(data,hits,asm)
        self.assertEqual(result[0]["loaded_addresses"],["0x40370004"])
        self.assertEqual(result[1]["loaded_addresses"],["0x42000000"])
        self.assertEqual(result[2]["loaded_addresses"],[])
        self.assertEqual([x["instruction_address"] for x in result[0]["explicit_literal_loads"]],["40370100"])
        self.assertEqual([x["instruction_address"] for x in result[1]["explicit_literal_loads"]],["40370103"])
        self.assertTrue(all(x["classification"]=="unresolved" for x in result))
        with self.assertRaisesRegex(ValueError,"truncated image segment"):
            mmio_literal_context(data[:-1],hits,asm)
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
