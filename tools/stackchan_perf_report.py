#!/usr/bin/env python3
"""Offline analysis of K151 PERF_TIME / PERF_MEM serial logs (Python 3.9+)."""
import argparse
import json
import re
import statistics
import sys
from pathlib import Path

TIME_FIELDS = ("seq window_ms frames fps_milli render_avg_us render_max_us "
               "flush_avg_us flush_max_us loop_avg_us loop_max_us slow_loops off dim game").split()
MEM_FIELDS = ("seq up_ms heap heap_min heap_largest psram psram_total "
              "psram_largest reset cpu_mhz").split()
MAX32 = 2**32-1

def parse(line):
    m = re.search(r"\b(PERF_TIME|PERF_MEM)\s+(.*)$", line.strip())
    if not m:
        return None
    kind, body = m.groups()
    fields = TIME_FIELDS if kind == "PERF_TIME" else MEM_FIELDS
    result = {}
    for token in body.split():
        k, sep, v = token.partition("=")
        if not sep or k not in fields or k in result or not re.fullmatch(r"[0-9]{1,10}", v):
            raise ValueError("invalid field")
        result[k] = int(v)
        if result[k] > MAX32:
            raise ValueError("counter out of range")
    if set(result) != set(fields):
        raise ValueError("missing fields")
    if kind == "PERF_TIME":
        d = result
        if any(d[k] not in (0,1) for k in ("off","dim","game")):
            raise ValueError("invalid state")
        expected = d["frames"]*1000000//d["window_ms"] if d["window_ms"] else 0
        if d["fps_milli"] != expected or (not d["window_ms"] and d["frames"]):
            raise ValueError("inconsistent FPS")
        for k in ("render","flush","loop"):
            if d[k+"_avg_us"] > d[k+"_max_us"]:
                raise ValueError("inconsistent timing")
    else:
        d = result
        if d["heap_min"] > d["heap"] or d["heap_largest"] > d["heap"] or not (
            d["psram_largest"] <= d["psram"] <= d["psram_total"]):
            raise ValueError("inconsistent memory")
    return kind, result

def trends(rows, key, threshold):
    values = [x[key] for x in rows]
    if not values:
        return None
    # Compare medians of first/last 20% rather than individual transient samples.
    n = max(1,len(values)//5)
    first = statistics.median(values[:n])
    last = statistics.median(values[-n:])
    drop = first-last
    return dict(first=values[0],last=values[-1],minimum=min(values),maximum=max(values),
                median_start=first,median_end=last,drop_bytes=drop,
                decline_review=len(values)>=10 and drop>=threshold)

def analyze(lines, min_minutes=60, heap_drop=32768, psram_drop=262144):
    # Streaming parser; pair only TIME then MEM with same seq.
    # MEM-only records are valid for PERF? while monitoring is off.
    groups = []
    group = None
    pending = None
    malformed = unmatched_time = standalone_mem = gaps = duplicates = 0
    boot_markers = 0
    last_mem = None
    for line in lines:
        if "TamaPoke fw v" in line:
            boot_markers += 1
            if pending is not None:
                unmatched_time += 1
                pending = None
            group = last_mem = None
        try:
            record = parse(line)
        except ValueError:
            malformed += 1
            continue
        if record is None:
            continue
        kind, d = record
        if kind == "PERF_TIME":
            if pending is not None:
                unmatched_time += 1
            pending = d
            continue
        seq, up = d["seq"], d["up_ms"]
        if last_mem is not None:
            old_seq, old_up = last_mem["seq"], last_mem["up_ms"]
            if seq == old_seq and up == old_up:
                duplicates += 1
                if pending is not None and pending["seq"] == seq:
                    pending = None
                continue
            # Natural millis rollover allowed only near uint32 boundary.
            rollover = old_up > MAX32-3600000 and up < 3600000 and seq > old_seq
            if seq <= old_seq or (up < old_up and not rollover):
                group = None
            elif seq > old_seq+1:
                gaps += seq-old_seq-1
        if group is None:
            group = {"memory":[],"pairs":[]}
            groups.append(group)
        group["memory"].append(d)
        last_mem = d
        if pending is not None and pending["seq"] == seq:
            group["pairs"].append((pending,d))
            pending = None
        else:
            standalone_mem += 1
            if pending is not None:
                unmatched_time += 1
                pending = None
    if pending is not None:
        unmatched_time += 1
    sessions = []
    for g in groups:
        mem, pairs = g["memory"],g["pairs"]
        # Snapshot flags are not per-frame classifications. Do not combine
        # dim/off windows into an active FPS estimate.
        phase = {}
        for name in ("active","game","dim","off"):
            windows = [t for t,_ in pairs if (
                "off" if t["off"] else "dim" if t["dim"] else "game" if t["game"] else "active"
            ) == name and t["window_ms"]>0]
            duration = sum(t["window_ms"] for t in windows)
            phase[name] = dict(windows=len(windows),duration_ms=duration,
                fps=sum(t["frames"] for t in windows)*1000/duration if duration else None,
                max_render_us=max((t["render_max_us"] for t in windows),default=None),
                max_flush_us=max((t["flush_max_us"] for t in windows),default=None),
                max_loop_us=max((t["loop_max_us"] for t in windows),default=None),
                slow_loops=sum(t["slow_loops"] for t in windows))
        # Bound by observed paired windows AND elapsed uptime span, allowing
        # the first measured window. No invented duration across missing data.
        observed = sum(t["window_ms"] for t,_ in pairs)
        span = sum((b["up_ms"]-a["up_ms"])&MAX32 for a,b in zip(mem,mem[1:]))
        first_window = pairs[0][0]["window_ms"] if pairs else 0
        covered = min(observed,span+first_window)
        # Ignore memory-only requests for trend comparisons if paired data exists.
        trend_rows = [m for _,m in pairs] or mem
        sessions.append(dict(memory_records=len(mem),paired_windows=len(pairs),
            coverage_ms=covered,uptime_span_ms=span,phases=phase,
            heap=trends(trend_rows,"heap",heap_drop),
            psram=trends(trend_rows,"psram",psram_drop),
            heap_largest=trends(trend_rows,"heap_largest",heap_drop),
            psram_largest=trends(trend_rows,"psram_largest",psram_drop),
            heap_min=min(m["heap_min"] for m in mem),
            reset_reasons=sorted({m["reset"] for m in mem})))
    reasons = []
    if len(sessions)!=1:
        reasons.append("no single uninterrupted telemetry session")
    if malformed or unmatched_time or gaps or duplicates:
        reasons.append("incomplete or ambiguous telemetry")
    if not sessions or max(s["coverage_ms"] for s in sessions)<min_minutes*60000:
        reasons.append("insufficient observed monitoring duration")
    if any(s[k] and s[k]["decline_review"] for s in sessions
           for k in ("heap","psram","heap_largest","psram_largest")):
        reasons.append("memory decline requires controlled workload review")
    if boot_markers>1:
        reasons.append("multiple boot markers observed")
    return dict(schema=1, status="review-required" if reasons else "telemetry-criteria-met",
                hardware_acceptance=False, minimum_minutes=min_minutes,
                malformed=malformed,unmatched_time=unmatched_time,
                standalone_mem=standalone_mem,missing_sequence_records=gaps,
                duplicate_records=duplicates,boot_markers=boot_markers,
                sessions=sessions,review_reasons=reasons)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("log",type=Path)
    p.add_argument("--minutes",type=int,default=60)
    p.add_argument("--heap-drop",type=int,default=32768)
    p.add_argument("--psram-drop",type=int,default=262144)
    p.add_argument("--out",type=Path)
    p.add_argument("--strict",action="store_true",help="exit 2 for review-required")
    a=p.parse_args()
    if min(a.minutes,a.heap_drop,a.psram_drop)<=0:
        p.error("thresholds must be positive")
    try:
        with a.log.open(encoding="utf-8",errors="replace") as f:
            report=analyze(f,a.minutes,a.heap_drop,a.psram_drop)
        payload=json.dumps(report,indent=2)+"\n"
        if a.out:
            with a.out.open("x",encoding="utf-8") as f:f.write(payload)
        else:print(payload,end="")
        return 2 if a.strict and report["review_reasons"] else 0
    except (OSError,ValueError) as exc:
        print(f"ERROR: {exc}",file=sys.stderr);return 1
if __name__=="__main__":
    sys.exit(main())
