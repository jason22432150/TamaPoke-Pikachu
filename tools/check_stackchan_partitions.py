import csv
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"boards/stackchan/partitions.csv"
rows=list(csv.reader(line for line in p.read_text().splitlines() if line and not line.startswith("#")))
end=0x9000
names=set()
for name,typ,sub,offset,size,*_ in rows:
    start,n=int(offset,0),int(size,0)
    assert name not in names and n>0 and start>=end and start%0x1000==0 and n%0x1000==0
    if typ=="app": assert start%0x10000==0
    names.add(name)
    end=start+n
    assert end<=0x1000000
assert end==0xe10000 and names=={"nvs","otadata","phy_init","ota_0","ota_1","assets","coredump"}
print("Observed K151 16 MiB partition layout: valid bounds and alignment")
