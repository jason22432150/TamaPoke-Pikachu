#pragma once
#include "servo_power_session.h"
namespace tpkbody {
// Supervised one-reaction bench coordinator; no runtime game caller.
// Power and output must be backed by the same exclusively owned transport.
enum class ReactionState:uint8_t { Locked, Powering, Waiting, Outbound, Returning, Complete, Fault, ShutdownUnconfirmed };
class ServoReactionSession {
  ServoPowerIO& io_;
  ServoPowerSession power_;
  ServoExecutor executor_;
  ReactionState state_=ReactionState::Locked;
  ServoCenters centers_{-1,-1};
  Reaction previous_=Reaction::None;
  uint32_t started_=0;
  static ExecutionGuard executionGuard(const PowerGuard& g){
    return {g.game,g.benchVerified&&g.physicalStopAvailable,true,g.exclusiveHardware};
  }
  ReactionState finish(bool fault){
    // Power owns the bus and performs release on both axes, rail off and close.
    // Do not call executor after power has closed the shared bus.
    auto p=power_.stop();
    state_=p==PowerState::ShutdownUnconfirmed?ReactionState::ShutdownUnconfirmed:
      fault||p==PowerState::Fault?ReactionState::Fault:ReactionState::Complete;
    return state_;
  }
public:
  ServoReactionSession(ServoPowerIO& io,ServoOutput& output):
    io_(io),power_(io),executor_(output){}
  ServoReactionSession(const ServoReactionSession&)=delete;
  ServoReactionSession& operator=(const ServoReactionSession&)=delete;
  ReactionState state()const{return state_;}
  bool begin(const PowerGuard& g,ServoCenters c,Reaction current){
    if(state_!=ReactionState::Locked)return false;
    started_=io_.clockMs();
    if(!power_.begin(g,c,started_)){
      if(power_.state()==PowerState::Fault||power_.state()==PowerState::ShutdownUnconfirmed)finish(true);
      return false;
    }
    centers_=c;previous_=current;state_=ReactionState::Powering;return true;
  }
  ReactionState tick(const PowerGuard& g,Reaction reaction){
    if(state_!=ReactionState::Powering&&state_!=ReactionState::Waiting&&
       state_!=ReactionState::Outbound&&state_!=ReactionState::Returning)return state_;
    uint32_t now=io_.clockMs();
    if(!powerAllowed(g)||now-started_>=SESSION_MS)return finish(true);
    auto p=power_.tick(g,now);
    if(p==PowerState::Settling){previous_=reaction;return state_;}
    if(p!=PowerState::Ready)return finish(true);
    PowerSample sample{};
    if(!io_.sample(sample))return finish(true);
    now=io_.clockMs();
    if(now-started_>=SESSION_MS)return finish(true);
    bool rail=false;
    if(!io_.readRailLatch(rail)||!rail)return finish(true);
    auto guard=executionGuard(g);
    if(state_==ReactionState::Powering){
      if(!executor_.arm(guard,centers_,sample.feedback,now))return finish(true);
      previous_=reaction;state_=ReactionState::Waiting;return state_;
    }
    if(executor_.update(guard,sample.feedback,now)!=ExecuteResult::Ok)return finish(true);
    if(state_==ReactionState::Waiting){
      bool edge=reaction!=previous_;previous_=reaction;
      if(!edge||reaction==Reaction::None)return state_;
      if(executor_.start(reactionPose(reaction),guard,sample.feedback,now)!=ExecuteResult::Ok)
        return finish(true);
      state_=ReactionState::Outbound;
    }else if(executor_.state()==ExecuteState::Complete){
      if(state_==ReactionState::Outbound){
        if(executor_.start({0,0,100},guard,sample.feedback,now)!=ExecuteResult::Ok)
          return finish(true);
        state_=ReactionState::Returning;
      }else return finish(false);
    }
    return state_;
  }
  ReactionState stop(){
    if(state_==ReactionState::Powering||state_==ReactionState::Waiting||
       state_==ReactionState::Outbound||state_==ReactionState::Returning)return finish(false);
    return state_;
  }
};
}
