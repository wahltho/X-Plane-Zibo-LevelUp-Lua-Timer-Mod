
#include "lua_helpers.h"
extern "C" {
#include "lualib.h"
}
#include "xptimers.h"
#include <XPLMDataAccess.h>
#include <cstdio>
#include <cstdarg>
#include <cstdlib>
#include <vector>
#include <string>
#include <cmath>
#include <fstream>
#include <iostream>
using std::vector;
static float simulated_time=0, period=0; static int replay=0;
static int time_token,period_token,replay_token;
XPLMDataRef g_sim_period=&period_token, g_replay_active=&replay_token;
extern "C" XPLMDataRef XPLMFindDataRef(const char*) {return &time_token;}
extern "C" float XPLMGetDataf(XPLMDataRef p) {return p==g_sim_period?period:simulated_time;}
extern "C" int XPLMGetDatai(XPLMDataRef) {return replay;}
int log_message(lua_State*,char const* const format,...) {va_list a;va_start(a,format);auto r=vfprintf(stderr,format,a);va_end(a);return r;}
static std::string phase; static vector<std::string> events;
static int record(lua_State* L){events.push_back(phase+":"+lua_tostring(L,1));return 0;}
#include "module.h"
void invoke(Callback &c){lua_getglobal(c.L,c.name.c_str());if(fmt_pcall_stdvars(c.L,0,"")) exit(2);}
static void dispatch(void* p){invoke(*(Callback*)p);}

static vector<module*> g_modules;
#include "master_callbacks2.inc"
static double number(lua_State* L,const char* n){lua_getglobal(L,n);double r=lua_tonumber(L,-1);lua_pop(L,1);return r;}
static void run(lua_State* L,const char* code){if(luaL_dostring(L,code)){fprintf(stderr,"%s\n",lua_tostring(L,-1));exit(2);}}
static lua_State* state(){auto L=luaL_newstate();luaL_openlibs(L);lua_pushcfunction(L,record);lua_setglobal(L,"record");run(L,R"(
function setup_callback_var(n,v) _G[n]=v end
before_count=0;after_count=0;elapsed=0;payload=0;lag=0;seen_replay=0
function before_physics() before_count=before_count+1; record('before') end
function after_physics() after_count=after_count+1; elapsed=elapsed+SIM_PERIOD;payload=payload+SIM_PERIOD*2000;lag=lag+SIM_PERIOD;seen_replay=seen_replay+IN_REPLAY;record('after') end
)");return L;}
static void tick(){phase="pre";xlua_pre_timer_master_cb(0,0,0,nullptr);phase="physics";events.push_back("physics");phase="post";xlua_post_timer_master_cb(0,0,0,nullptr);}
int main(int argc,char** argv){

if(argc>2 && std::string(argv[1])=="--own") {
 int assertions=0;auto check=[&](bool condition,const char* label){if(!condition){std::cerr<<"FAIL "<<label<<"\n";exit(4);}assertions++;};
 for(int fps:{10,20,30,60,120}) {
  simulated_time=0;period=1.0f/fps;replay=0;events.clear();auto L=state();
  lua_pushstring(L,argv[2]);lua_setglobal(L,"project_root");
  run(L,R"(
   jit.off()
   local M=dofile(project_root .. '/modules/lua-timer/payload/B738.wahltho_timer.lua')
   local geometry=M.wrap4(function(a,b,c,d) return math.sin(a)+math.cos(b)+math.sin(c)+math.cos(d) end,function() return callback_clock end)
   function before_physics() before_count=before_count+1; geometry(1,2,3,4);record('before') end
  )");
  module m{{L,"before_physics"},{L,"after_physics"},true,true};g_modules={&m};
  for(int i=1;i<=fps*60;i++){simulated_time=(float)i/fps;lua_pushnumber(L,simulated_time);lua_setglobal(L,"callback_clock");tick();}
  check(std::abs(number(L,"elapsed")-60)<.001,"SIM_PERIOD accumulates 60 seconds");
  check(number(L,"before_count")==fps*60&&number(L,"after_count")==fps*60,"callbacks retain full frame rate");
  check(std::abs(number(L,"payload")-120000)<1,"frame-rate payload rate unchanged");
  events.clear();simulated_time+=period;tick();check(events==vector<std::string>{"pre:before","physics","post:after"},"before/after phases preserved");
  double count=number(L,"after_count");replay=1;simulated_time+=1;tick();check(number(L,"after_count")==count,"replay gating preserved");
  replay=0;period=0;simulated_time+=1;tick();check(number(L,"after_count")==count,"paused zero-period gating preserved");
  period=.4f;simulated_time+=period;tick();check(std::abs(number(L,"elapsed")-(60+1.0/fps+.4))<.001,"dropped-frame period preserved");
  std::cout<<"PASS own-runtime fps="<<fps<<" elapsed="<<number(L,"elapsed")<<"\n";
  xlua_timer_cleanup();g_modules.clear();lua_close(L);
 }
 std::cout<<"PASS native assertions="<<assertions<<"\n";return 0;
}

if(argc>2 && std::string(argv[1])=="--execute"){auto L=luaL_newstate();luaL_openlibs(L);if(luaL_dofile(L,argv[2])){std::cerr<<lua_tostring(L,-1)<<"\n";return 5;}lua_close(L);return 0;}
if(argc>1){auto L=luaL_newstate();for(int i=1;i<argc;i++){int r=luaL_loadfile(L,argv[i]);std::cout<<(r?"FAIL ":"PASS ")<<argv[i];if(r) std::cout<<" "<<lua_tostring(L,-1);std::cout<<"\n";if(r)return 3;lua_settop(L,0);}lua_close(L);return 0;}
int assertions=0;auto check=[&](bool p,const char* n){if(!p){std::cerr<<"FAIL "<<n<<"\n";exit(4);}assertions++;};
for(int fps:{20,30,60,120}) for(bool timer:{false,true}) {
simulated_time=0;period=1.0f/fps;replay=0;events.clear();auto L=state();module m{{L,"before_physics"},{L,"after_physics"},!timer,!timer};g_modules={&m};
Callback b{L,"before_physics"},a{L,"after_physics"};
if(timer){xlua_run_timer(xlua_create_timer(L,dispatch,&b),.05,.05);xlua_run_timer(xlua_create_timer(L,dispatch,&a),.05,.05);}
for(int i=1;i<=fps*60;i++){simulated_time=(float)i/fps;tick();}
std::cout<<"{\"fps\":"<<fps<<",\"timer\":"<<(timer?"true":"false")<<",\"real_seconds\":60,\"calls\":"<<number(L,"after_count")<<",\"accumulated_SIM_PERIOD\":"<<number(L,"elapsed")<<",\"payload_delta_kg\":"<<number(L,"payload")<<"}\n";
if(timer){check(std::abs(number(L,"elapsed")-1200.0/fps)<.11,"timer uses frame period not interval");}
else check(std::abs(number(L,"elapsed")-60)<.001,"original advances sixty seconds");
xlua_timer_cleanup();g_modules.clear();lua_close(L);
}
simulated_time=0;period=.05;replay=0;auto L=state();module m{{L,"before_physics"},{L,"after_physics"},true,true};g_modules={&m};Callback b{L,"before_physics"},a{L,"after_physics"};
events.clear();simulated_time=.05;tick();check(events==vector<std::string>{"pre:before","physics","post:after"},"original phases");
m.before=false;m.after=false;simulated_time=0;xlua_run_timer(xlua_create_timer(L,dispatch,&b),.05,.05);xlua_run_timer(xlua_create_timer(L,dispatch,&a),.05,.05);
events.clear();simulated_time=.05;tick();for(auto &e:events)std::cout<<"event "<<e<<"\n";
check(events==vector<std::string>{"pre:after","pre:before","physics"},"timer reverses callback order and moves after before physics");
replay=1;auto prior=number(L,"after_count");simulated_time=.11;tick();check(number(L,"after_count")==prior+1 && number(L,"seen_replay")==1,"timed callback runs during replay");
xlua_timer_cleanup();m.before=true;m.after=true;prior=number(L,"after_count");simulated_time=.2;tick();check(number(L,"after_count")==prior,"original callbacks suppressed during replay");
replay=0;m.before=false;m.after=false;simulated_time=.2;xlua_run_timer(xlua_create_timer(L,dispatch,&a),.05,.05);simulated_time=.26;tick();prior=number(L,"after_count");for(int i=0;i<20;i++)tick();check(number(L,"after_count")==prior,"frozen simulator clock does not fire more timers");
simulated_time=1;tick();check(number(L,"after_count")==prior+1,"overdue timer fires once per frame");
period=0;prior=number(L,"after_count");simulated_time=1.05;tick();check(number(L,"after_count")==prior+1,"timers lack zero SIM_PERIOD gate when clock advances");
xlua_timer_cleanup();g_modules.clear();lua_close(L);std::cout<<"PASS assertions="<<assertions<<"\n";
}
