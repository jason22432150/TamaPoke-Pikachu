#pragma once
#include <M5Unified.h>
#include "src/drivers/FTServo_Arduino/src/SCSCL.h"
#include "servo_diagnostic_policy.h"

namespace tpkbody {
// Only the read paths of the pinned official BSP driver are exposed here.
// Never call servo_init(), setServoPowerEnabled(), WritePos(), EnableTorque(),
// SwitchMode(), Recal() or any EEPROM/register write.
class ServoDiagnostic {
  ServoProbePolicy policy_;
  SCSCL bus_;
  static bool railState(bool& on) {
    uint8_t mode=0,latch=0;
    // PY32 BSP 1.1.0: GPIO mode 0x03, output latch 0x05, VM EN bit 0.
    // Require successful reads and output mode; latch is not a voltage measurement.
    if(!m5::In_I2C.readRegister(0x6F,0x03,&mode,1,100000) ||
       !m5::In_I2C.readRegister(0x6F,0x05,&latch,1,100000) || !(mode&1))
      return false;
    on=(latch&1)!=0;
    return true;
  }
  bool readServo(uint8_t id,ServoFeedback& f) {
    if(bus_.Ping(id)!=id || bus_.getLastError()!=0 || bus_.getState()!=0)return false;
    if(bus_.FeedBack(id)<0 || bus_.getLastError()!=0 || bus_.getState()!=0)return false;
    f={bus_.ReadPos(-1),bus_.ReadVoltage(-1),bus_.ReadTemper(-1),bus_.ReadMove(-1),-1};
    // BSP ReadToqueEnable uses readWord; the torque register is one byte.
    f.torque=bus_.readByte(id,SCSCL_TORQUE_ENABLE);
    return f.torque>=0 && bus_.getLastError()==0 && bus_.getState()==0;
  }
  static void print(uint8_t id,const ServoFeedback& f) {
    Serial.printf("SERVO id=%u raw_position=%d voltage_raw=%d temperature_raw=%d moving=%d torque=%d\n",
        unsigned(id),f.position,f.voltage,f.temperature,f.moving,f.torque);
  }
public:
  void probe(bool awake,bool previewOff,int battery) {
    bool railOn=false;
    bool correct=M5.getBoard()==m5gfx::board_t::board_M5StackChan;
    bool known=correct && railState(railOn);
    bool free=!uart_is_driver_installed(UART_NUM_1);
    auto result=policy_.begin({correct,known,railOn,free,awake,previewOff,battery},millis());
    if(result!=ProbeResult::Ok) {
      Serial.printf("ERR SERVO PROBE code=%u rail_known=%d rail_latch=%d uart_free=%d\n",
          unsigned(result),known,railOn,free);
      return;
    }
    ServoFeedback yaw{-1,-1,-1,-1,-1},pitch=yaw;
    // UART configuration comes directly from the official K151 BSP.
    bus_.IOTimeOut=10;
    bool opened=bus_.begin(UART_NUM_1,1000000,6,7);
    bool ok=false;
    if(opened) {
      ok=readServo(1,yaw) && feedbackValid(yaw) && readServo(2,pitch);
      bus_.end();
    }
    // No automatic retry. A communication/feedback fault stays latched until reboot.
    result=policy_.finish(ok,yaw,pitch);
    if(result!=ProbeResult::Ok) {
      Serial.printf("ERR SERVO PROBE code=%u fault latched until reboot\n",unsigned(result));
      return;
    }
    print(1,yaw);print(2,pitch);
    Serial.println("DONE read-only servo feedback; motion disabled");
  }
};
}
