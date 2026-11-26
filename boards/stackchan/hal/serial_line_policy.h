#pragma once
#include <stdint.h>
#include <stddef.h>
namespace tpkserial {
enum class Result { Pending, Ready, Rejected };
// LF is the only delimiter; CRLF is accepted, embedded CR/control bytes
// reject the entire line. Never dispatch a truncated or timed-out suffix.
class Line {
  char data_[257]{};
  size_t len_=0;
  bool invalid_=false,cr_=false;
  uint32_t accepted_=0,rejected_=0;
public:
  Result feed(uint8_t c){
    if(c=='\n'){
      data_[len_]=0;
      Result r=invalid_?Result::Rejected:len_?Result::Ready:Result::Pending;
      if(r==Result::Ready)++accepted_;
      if(r==Result::Rejected)++rejected_;
      len_=0;invalid_=false;cr_=false;return r;
    }
    if(invalid_)return Result::Pending;
    if(cr_){invalid_=true;return Result::Pending;}
    if(c=='\r'){cr_=true;return Result::Pending;}
    if((c<32&&c!='\t')||c==127||len_>=sizeof(data_)-1){invalid_=true;return Result::Pending;}
    data_[len_++]=char(c);
    return Result::Pending;
  }
  const char* text()const{return data_;}
  size_t pending()const{return len_;}
  bool discarding()const{return invalid_;}
  uint32_t accepted()const{return accepted_;}
  uint32_t rejected()const{return rejected_;}
};
}
