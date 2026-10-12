#pragma once
#include <vector>
#include <string>
#include "lua_helpers.h"
struct Callback {lua_State* L;std::string name;};
void invoke(Callback &c);
struct module {Callback pre,post;bool before,after;static module* module_from_interp(lua_State*) {static module legacy{};return &legacy;} const std::vector<int>& get_required_version() const {static const std::vector<int> v{1,0,0};return v;} bool has_pre_physics(){return before;}bool has_post_physics(){return after;}bool has_post_replay(){return false;}void pre_physics(){invoke(pre);}void post_physics(){invoke(post);}void post_replay(){}};
