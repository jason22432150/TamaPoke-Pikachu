from stackchan_review import expected_layout
# Independent observed device geometry, not inferred from candidate CSV.
expected=[
    ("nvs",1,2,0x9000,0x4000,0),
    ("otadata",1,0,0xd000,0x2000,0),
    ("phy_init",1,1,0xf000,0x1000,0),
    ("ota_0",0,16,0x20000,0x4f0000,0),
    ("ota_1",0,17,0x510000,0x4f0000,0),
    ("assets",1,130,0xa00000,0x400000,0),
    ("coredump",1,3,0xe00000,0x10000,0)]
actual=[tuple(p[k] for k in ("label","type","subtype","offset","size","flags")) for p in expected_layout()]
if actual!=expected:
    raise SystemExit("K151 partition map differs from observed device")
print("Observed K151 16 MiB partition layout: exact match")
