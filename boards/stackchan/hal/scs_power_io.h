#pragma once
#include <M5Unified.h>
#include "src/drivers/FTServo_Arduino/src/SCSCL.h"
#include "servo_power_session.h"

namespace tpkbody {
// Compile-only bench adapter. Never instantiated by game. The caller must
// ensure exclusive access to UART1 and the PY32 shared GPIO register.
class ScsPowerIO final:public ServoPowerIO {
  SCSCL bus_;
  bool opened_=false;
  static bool boardOk(){return M5.getBoard()==m5gfx::board_t::board_M5StackChan;}
  static bool readLatch(uint8_t& value){
    uint8_t mode=0;
    return boardOk() && m5::In_I2C.readRegister(0x6F,0x03,&mode,1,100000) &&
      (mode&1) && m5::In_I2C.readRegister(0x6F,0x05,&value,1,100000);
  }
  bool ack(int r){return r==1&&bus_.Level==1&&bus_.getState()==0&&bus_.getLastError()==0;}
  bool readOk(int value){return value>=0&&bus_.getState()==0&&bus_.getLastError()==0;}
  bool readAxis(uint8_t id,ServoFeedback& f,RawRange& range,int& goal){
    int ping=bus_.Ping(id);
    if(ping!=id||!readOk(ping)||!readOk(bus_.FeedBack(id)))return false;
    f={bus_.ReadPos(-1),bus_.ReadVoltage(-1),bus_.ReadTemper(-1),bus_.ReadMove(-1),-1};
    f.torque=bus_.readByte(id,SCSCL_TORQUE_ENABLE);if(!readOk(f.torque))return false;
    range.lo=bus_.readWord(id,SCSCL_MIN_ANGLE_LIMIT_L);if(!readOk(range.lo))return false;
    range.hi=bus_.readWord(id,SCSCL_MAX_ANGLE_LIMIT_L);if(!readOk(range.hi))return false;
    goal=bus_.readWord(id,SCSCL_GOAL_POSITION_L);
    return readOk(goal)&&feedbackValid(f);
  }
public:
  bool readRailLatch(bool& on)override{
    uint8_t latch=0;if(!readLatch(latch))return false;
    on=(latch&1)!=0;return true;
  }
  bool openBus()override{
    if(opened_||!boardOk()||uart_is_driver_installed(UART_NUM_1))return false;
    bus_.IOTimeOut=10;
    opened_=bus_.begin(UART_NUM_1,1000000,6,7);return opened_;
  }
  void closeBus()override{if(opened_)bus_.end();opened_=false;}
  bool setRailLatch(bool on)override{
    uint8_t old=0;if(!opened_||!readLatch(old))return false;
    // Never configure GPIO mode or pulls. Preserve other output bits.
    uint8_t next=on?uint8_t(old|1):uint8_t(old&~1);
    if(!m5::In_I2C.writeRegister8(0x6F,0x05,next,100000))return false;
    uint8_t actual=0;return readLatch(actual)&&actual==next;
  }
  uint32_t clockMs()override{return millis();}
  bool sample(PowerSample& data)override{
    if(!opened_)return false;
    uint32_t start=millis();
    if(!readAxis(1,data.feedback.yaw,data.feedback.yawRange,data.goal.yaw)||
       !readAxis(2,data.feedback.pitch,data.feedback.pitchRange,data.goal.pitch))return false;
    data.feedback.sampledAt=start;
    return millis()-start<=FEEDBACK_MAX_MS;
  }
  bool setTorque(uint8_t id,bool on)override{
    if(!opened_||(id!=1&&id!=2)||!ack(bus_.EnableTorque(id,on?1:0)))return false;
    int result=bus_.readByte(id,SCSCL_TORQUE_ENABLE);
    return readOk(result)&&result==int(on);
  }
};
}
