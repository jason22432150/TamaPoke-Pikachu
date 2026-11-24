#pragma once
#include "servo_executor.h"
#include "src/drivers/FTServo_Arduino/src/SCSCL.h"
namespace tpkbody {
// Compile-checked adapter only: NOT instantiated by game firmware. The caller
// must own an initialized UART, confirmed rail and reviewed bench interlock.
class ScsOutput final:public ServoOutput {
  SCSCL& bus_;
  bool ack(int result) const {
    return result==1 && bus_.Level==1 && bus_.getLastError()==0 && bus_.getState()==0;
  }
public:
  explicit ScsOutput(SCSCL& bus):bus_(bus){}
  bool writePosition(uint8_t id,uint16_t raw,uint16_t durationMs) override {
    if((id!=1&&id!=2)||raw>1000||durationMs!=COMMAND_TIME_MS||
       bus_.Level!=1||bus_.uart_num!=UART_NUM_1||!uart_is_driver_installed(UART_NUM_1))return false;
    return ack(bus_.WritePos(id,raw,durationMs,0));
  }
  bool releaseTorque(uint8_t id) override {
    if((id!=1&&id!=2)||bus_.Level!=1||bus_.uart_num!=UART_NUM_1||
       !uart_is_driver_installed(UART_NUM_1))return false;
    if(!ack(bus_.EnableTorque(id,0)))return false;
    // Verify the single-byte register, not just the write acknowledgement.
    int value=bus_.readByte(id,SCSCL_TORQUE_ENABLE);
    return value==0 && bus_.getLastError()==0 && bus_.getState()==0;
  }
};
}
