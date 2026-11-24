#include "StackChanSmoke/board_hal.h"
#include <cassert>
int main() {
  auto a=toLogical({40,0,true}); assert(a.valid && a.x==0 && a.y==0);
  auto b=toLogical({279,239,true}); assert(b.valid && b.x==465 && b.y==465);
  assert(!toLogical({39,0,true}).valid);
  assert(!toLogical({280,0,true}).valid);
  assert(!toLogical({40,240,true}).valid);
  assert(!toLogical({40,0,false}).valid);
}
