#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <esp_partition.h>
#include <Arduino.h>
#include "sd_upload_policy.h"

// The factory table keeps subtype 0x82 and label assets unchanged.
// TPAS is a raw immutable archive, not an SPIFFS filesystem.
namespace tpkassets {
constexpr uint32_t Capacity=0x400000, Count=303, Start=16+Count*12;
inline uint32_t u32(const uint8_t* p) {
  return uint32_t(p[0]) | uint32_t(p[1])<<8 | uint32_t(p[2])<<16 | uint32_t(p[3])<<24;
}
inline const esp_partition_t* partition() {
  const auto* p=esp_partition_find_first(ESP_PARTITION_TYPE_DATA,
                                        ESP_PARTITION_SUBTYPE_DATA_SPIFFS,"assets");
  return p && p->address==0xa00000 && p->size==Capacity ? p : nullptr;
}
inline bool ready() {
  const auto* p=partition();
  uint8_t h[16];
  return p && esp_partition_read(p,0,h,sizeof h)==ESP_OK &&
    memcmp(h,"TPAS",4)==0 && u32(h+4)==1 && u32(h+8)==Count && u32(h+12)==Start;
}
inline uint8_t* load(uint16_t id,uint32_t& size) {
  size=0;
  if(id>=Count || !ready())return nullptr;
  const auto* p=partition();
  uint8_t e[12];
  if(!p || esp_partition_read(p,16+id*12,e,sizeof e)!=ESP_OK)return nullptr;
  const uint32_t off=u32(e),n=u32(e+4),crc=u32(e+8);
  if(off<Start || off>=Capacity || n>Capacity-off ||
     n<(id?7u:10u) || n>(id?3u:2u)*1024*1024)return nullptr;
  uint8_t* data=(uint8_t*)ps_malloc(n);
  if(!data)return nullptr;
  if(esp_partition_read(p,off,data,n)!=ESP_OK ||
     (tpksd::crc32(0xffffffffu,data,n)^0xffffffffu)!=crc ||
     memcmp(data,id?"TPK2":"TPTH",4)!=0) {free(data);return nullptr;}
  size=n;return data;
}
}
