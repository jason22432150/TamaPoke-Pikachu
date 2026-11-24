import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from stackchan_backup import (ARCHIVE,COPY,FLASH_BYTES,TABLE_BYTES,TABLE_OFFSET,
                              capture,verify,parse_table)


def entry(offset=0x9000,size=0x5000,kind=1):
    return struct.pack("<HBBII16sI",0x50AA,kind,2,offset,size,b"nvs",0)


def table(entries):
    data=b"".join(entries)
    return (data+b"\xeb\xeb"+b"\xff"*14+hashlib.md5(data).digest()).ljust(TABLE_BYTES,b"\xff")


class BackupTests(unittest.TestCase):
    def test_table(self):
        self.assertEqual(parse_table(table([entry()]))[0]["label"],"nvs")
        for bad in (table([entry(),entry()]),table([entry(FLASH_BYTES)]),
                    table([entry(0x9001)]),table([entry(0x9000,0x5000,0)]),
                    b"\xff"*TABLE_BYTES):
            with self.assertRaises(ValueError): parse_table(bad)
        b=bytearray(table([entry()]));b[48]^=1
        with self.assertRaises(ValueError): parse_table(b)

    def make_runner(self, mismatch=False, small=False, wrong_mac=False, wrong_flash=False):
        calls=[]
        def run(args,path):
            commands=("version","read-mac","get-security-info","flash-id","read-flash")
            command=next(a for a in args if a in commands)
            calls.append(command)
            if command=="version": report="esptool v5.1.0"
            elif command=="read-mac":
                report="MAC: 00:11:22:33:44:66" if wrong_mac and calls.count(command)>1 else "MAC: 00:11:22:33:44:55"
            elif command=="flash-id": report="Detected flash size: "+("8MB" if wrong_flash else "16MB")
            elif command=="get-security-info": report="security test"
            else:
                dest=Path(args[-1])
                with dest.open("wb") as f:
                    f.truncate(100 if small else FLASH_BYTES)
                    if not small:
                        f.seek(TABLE_OFFSET);f.write(table([entry()]))
                        if mismatch and dest.name==COPY:
                            f.seek(0);f.write(b"X")
                report="read successful"
            path.write_text(report)
            return report
        return run,calls

    def test_matching_and_tampered(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/"backup"
            run,calls=self.make_runner()
            m=capture("fake",out,runner=run)
            self.assertEqual(verify(out),m)
            self.assertFalse(m["restore_authorized"])
            self.assertEqual(calls,["version","read-mac","get-security-info","flash-id","read-flash","read-flash","read-mac"])
            self.assertEqual(json.loads((out/"partitions.json").read_text())["status"],"candidate-md5-valid")
            with self.assertRaises(FileExistsError): capture("fake",out,runner=run)
            with (out/ARCHIVE).open("r+b") as f: f.write(b"X")
            with self.assertRaises(ValueError): verify(out)

    def test_fail_closed(self):
        for options in ({"mismatch":True},{"small":True},{"wrong_mac":True},{"wrong_flash":True}):
            with self.subTest(options=options), tempfile.TemporaryDirectory() as tmp:
                out=Path(tmp)/"backup"
                run,_=self.make_runner(**options)
                with self.assertRaises(ValueError): capture("fake",out,runner=run)
                self.assertFalse((out/"manifest.json").exists())


if __name__=="__main__":
    unittest.main()
