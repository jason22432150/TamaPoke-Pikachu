#include "hal/sd_upload_policy.h"
#include <cassert>
#include <set>
#include <string>
using namespace tpksd;
struct Fake {
  std::set<std::string> files;
  int renameCount=0,failRename=0,failRename2=0;
  bool failRemove=false;
  bool exists(const char* p){return files.count(p);}
  bool rename(const char* a,const char* b){
    ++renameCount;
    if(renameCount==failRename||renameCount==failRename2||!exists(a)||exists(b))return false;
    files.erase(a);files.insert(b);return true;
  }
  bool remove(const char* p){return !failRemove&&files.erase(p);}
};
int main(){
  assert(classify("/mons/001.bin")==Kind::Tpk1);
  assert(classify("/mons/s151.bin")==Kind::Tpk1);
  assert(classify("/mons/ps025.bin")==Kind::Tpk2);
  assert(classify("/mons/p001.bin")==Kind::Tpk2);
  assert(classify("/mons/thumbs.bin")==Kind::Thumbs);
  for(auto p:{"/mons/../x.bin","/mons/a/b.bin","/mons/000.bin","/mons/p152.bin",
      "/mons/025.bin.bak","/mons/P025.bin","/mons/025.bin ","/mons/025.BIN","/mons/","/mons/s"})
    assert(classify(p)==Kind::Invalid);
  uint32_t n=0;assert(parseSize("4194304",n)&&n==4194304);
  for(auto p:{"0","-1","4194305","99999999999999999","12abc"," 12",""})
    assert(!parseSize(p,n));
  const uint8_t b[]="123456789";
  assert((crc32(0xffffffffu,b,9)^0xffffffffu)==0xcbf43926u);
  const uint8_t t[]="TPK2abc";
  assert(headerOk(Kind::Tpk2,t,7,7));
  assert(!headerOk(Kind::Tpk1,t,7,7));
  Fake f;f.files={"target","stage"};
  assert(replace(f,"target","stage","backup")==Commit::Done&&f.files==std::set<std::string>{"target"});
  Fake g;g.files={"target","stage"};g.failRename=2;
  assert(replace(g,"target","stage","backup")==Commit::Failed&&g.exists("target")&&g.exists("stage"));
  Fake h;h.files={"target","stage"};h.failRename=2;h.failRename2=3;
  assert(replace(h,"target","stage","backup")==Commit::RecoveryRequired&&h.exists("backup")&&h.exists("stage"));
  Fake j;j.files={"target","stage"};j.failRemove=true;
  assert(replace(j,"target","stage","backup")==Commit::CleanupRequired&&j.exists("target")&&j.exists("backup"));
  Fake k;k.files={"backup","stage"};assert(replace(k,"target","stage","backup")==Commit::RecoveryRequired&&k.renameCount==0);
  Fake l;l.files={"stage"};assert(replace(l,"target","stage","backup")==Commit::Done&&l.exists("target"));
}
