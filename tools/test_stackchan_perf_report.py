import unittest
from stackchan_perf_report import analyze,parse,MAX32

def pair(seq,up,heap=180000,psram=6000000,off=0,dim=0,game=0):
    frames=0 if off else 50
    return [
        f"PERF_TIME seq={seq} window_ms=5000 frames={frames} fps_milli={frames*200} "
        f"render_avg_us=20000 render_max_us=30000 flush_avg_us=10000 flush_max_us=15000 "
        f"loop_avg_us=2000 loop_max_us=50000 slow_loops=0 off={off} dim={dim} game={game}",
        f"PERF_MEM seq={seq} up_ms={up} heap={heap} heap_min=100000 heap_largest={heap//2} "
        f"psram={psram} psram_total=8388608 psram_largest={psram//2} reset=1 cpu_mhz=240"
    ]

class ReportTests(unittest.TestCase):
    def test_normal(self):
        lines=[]
        for i in range(12):lines+=pair(i+1,(i+1)*5000,off=int(i>=6))
        r=analyze(lines,1)
        self.assertEqual(r["status"],"telemetry-criteria-met")
        self.assertFalse(r["hardware_acceptance"])
        self.assertEqual(r["sessions"][0]["coverage_ms"],60000)
        self.assertEqual(r["sessions"][0]["phases"]["active"]["fps"],10)
        self.assertEqual(r["sessions"][0]["phases"]["off"]["fps"],0)
    def test_decline(self):
        lines=[]
        for i in range(12):lines+=pair(i+1,(i+1)*5000,180000-i*5000,6000000-i*40000)
        r=analyze(lines,1)
        self.assertTrue(r["sessions"][0]["heap"]["decline_review"])
        self.assertTrue(r["sessions"][0]["psram"]["decline_review"])
        self.assertEqual(r["status"],"review-required")
    def test_gap_corrupt_reboot(self):
        lines=pair(1,5000)+pair(3,15000)+["PERF_TIME seq=4","TamaPoke fw v1"]+pair(1,5000)
        r=analyze(lines,1)
        self.assertEqual(r["missing_sequence_records"],1)
        self.assertEqual(r["malformed"],1)
        self.assertEqual(len(r["sessions"]),2)
        self.assertEqual(r["status"],"review-required")
    def test_rollover(self):
        r=analyze(pair(1,MAX32-4999)+pair(2,0),1)
        self.assertEqual(len(r["sessions"]),1)
        self.assertEqual(r["sessions"][0]["coverage_ms"],10000)
    def test_unmatched_and_memory_only(self):
        a=pair(1,5000)
        r=analyze([a[0],pair(2,10000)[1]])
        self.assertEqual(r["unmatched_time"],1)
        self.assertEqual(r["standalone_mem"],1)
        self.assertEqual(r["sessions"][0]["paired_windows"],0)
    def test_overlapping_windows_after_gap(self):
        lines = pair(1,5000)+pair(2,65000)+pair(3,66000)
        report = analyze(lines,1)
        self.assertEqual(report["sessions"][0]["coverage_ms"],11000)
    def test_corrupt_record_breaks_pair(self):
        a=pair(1,5000)
        report=analyze([a[0],"PERF_MEM seq=1",a[1]])
        self.assertEqual(report["unmatched_time"],1)
        self.assertEqual(report["sessions"][0]["paired_windows"],0)
    def test_invalid(self):
        a=pair(1,5000)
        for line in (a[0]+" seq=1",a[0].replace("fps_milli=10000","fps_milli=1"),
                     a[1].replace("psram_total=8388608","psram_total=1")):
            with self.assertRaises(ValueError):parse(line)
        self.assertEqual(analyze([])["status"],"review-required")
if __name__=="__main__":
    unittest.main()
