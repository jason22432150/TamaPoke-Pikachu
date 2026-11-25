#pragma once
#include "home_dialog_policy.h"
namespace tpkmini {
// Rectangular playfield in the same logical coordinate system sampled by B2.
// No action may originate from a clipped edge or a hidden control.
constexpr int BALL_HALF=24, LEFT=30, RIGHT=435, CEILING=88, FLOOR=270;
constexpr int SPAWN_Y=112, PET_Y=305, HIT_RADIUS=74;
constexpr tpkhome::Rect EXIT={344,8,108,50};
constexpr tpkhome::Rect BAG_HIT={130,63,206,185};
constexpr tpkhome::Rect RESULT_BACK={132,248,202,55};
constexpr int BAG_TOP=78,BAG_W=84,BAG_H=150;
static_assert(tpkhome::visible(EXIT)&&tpkhome::visible(BAG_HIT)&&
  tpkhome::visible(RESULT_BACK),"minigame controls fit");
static_assert(LEFT-BALL_HALF>=0&&RIGHT+BALL_HALF<GAME_SIZE&&
  CEILING-BALL_HALF>=EXIT.y+EXIT.h&&FLOOR+BALL_HALF<=logicalAxis(HOME_H-1)&&
  PET_Y<=logicalAxis(HOME_H-1),"ball and pet stay visible");
inline bool hitBall(float bx,float by,int x,int y){
  if(x<0||x>=GAME_SIZE||y<EXIT.y+EXIT.h||y>logicalAxis(HOME_H-1))return false;
  float dx=bx-x,dy=by-y;
  return dx*dx+dy*dy<HIT_RADIUS*HIT_RADIUS;
}
// Floor is a miss, not a bounce. Only reflect outward-moving velocity.
inline bool walls(float& x,float& y,float& vx,float& vy){
  if(x<LEFT){x=LEFT;if(vx<0)vx=-vx*0.85f;}
  if(x>RIGHT){x=RIGHT;if(vx>0)vx=-vx*0.85f;}
  if(y<CEILING){y=CEILING;if(vy<0)vy=-vy*0.85f;}
  return y>FLOOR;
}
inline uint8_t nextScore(uint8_t score){return score==UINT8_MAX?score:uint8_t(score+1);}
}
