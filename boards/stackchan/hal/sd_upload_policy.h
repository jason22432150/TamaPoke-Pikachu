#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
namespace tpksd {
enum class Kind { Invalid, Tpk1, Tpk2, Thumbs };
inline Kind classify(const char* path){
  if(!path || strncmp(path,"/mons/",6)!=0)return Kind::Invalid;
  const char* p=path+6;
  if(strcmp(p,"thumbs.bin")==0)return Kind::Thumbs;
  bool pmd=*p=='p';if(pmd)++p;
  if(*p=='s')++p;
  if(strlen(p)!=7||strcmp(p+3,".bin")!=0)return Kind::Invalid;
  int n=0;
  for(int i=0;i<3;i++){if(p[i]<'0'||p[i]>'9')return Kind::Invalid;n=n*10+p[i]-'0';}
  if(n<1||n>151)return Kind::Invalid;
  return pmd?Kind::Tpk2:Kind::Tpk1;
}
inline bool parseSize(const char* s,uint32_t& size){
  if(!s||!*s)return false;
  uint32_t n=0;
  for(;*s;++s){
    if(*s<'0'||*s>'9')return false;
    if(n>(4194304u-uint32_t(*s-'0'))/10u)return false;
    n=n*10+uint32_t(*s-'0');
  }
  if(!n)return false;
  size=n;return true;
}
inline bool headerOk(Kind k,const uint8_t* b,size_t n,uint32_t size){
  switch(k){
    case Kind::Tpk1:return n>=14 && size>=14 && memcmp(b,"TPK1",4)==0;
    case Kind::Tpk2:return n>=7 && size>=7 && size<=3u*1024*1024 && memcmp(b,"TPK2",4)==0;
    case Kind::Thumbs:return n>=10 && size>=10 && size<=2u*1024*1024 && memcmp(b,"TPTH",4)==0;
    default:return false;
  }
}
inline uint32_t crc32(uint32_t crc,const uint8_t* p,size_t n){
  while(n--){crc^=*p++;for(int i=0;i<8;i++)crc=(crc>>1)^(0xEDB88320u & (0u-(crc&1u)));}
  return crc;
}
// The staged file has already passed full read-back verification. The
// backup name must be absent; preserve artifacts on any ambiguous failure.
enum class Commit { Done, Failed, RecoveryRequired, CleanupRequired };
template<class FS> Commit replace(FS& fs,const char* target,const char* stage,const char* backup){
  if(fs.exists(backup)||!fs.exists(stage))return Commit::RecoveryRequired;
  bool had=fs.exists(target);
  if(had&&!fs.rename(target,backup))return Commit::RecoveryRequired;
  if(!fs.rename(stage,target)){
    if(had && !fs.exists(target) && fs.exists(backup)){
      if(!fs.rename(backup,target))return Commit::RecoveryRequired;
    }else if(had||fs.exists(target))return Commit::RecoveryRequired;
    return Commit::Failed;
  }
  if(!fs.exists(target)||fs.exists(stage))return Commit::RecoveryRequired;
  if(had && (!fs.exists(backup)||!fs.remove(backup)))return Commit::CleanupRequired;
  return Commit::Done;
}
}
