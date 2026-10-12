-- Executed with the actual LuaJIT/Lua 5.1 library used by XLua.
jit.off()
local root = os.getenv("TIMER_PROJECT_ROOT")
local M = dofile(root .. "/modules/lua-timer/payload/B738.wahltho_timer.lua")
assert(B738_wahltho_timer_module == M)
local total = 0
local function check(value, label)
    assert(value, label)
    total = total + 1
end
local now, calls, throw = 0, 0, false
local function original(a, b, c, d)
    calls = calls + 1
    if throw then error("original error") end
    return a + b + c + d
end
local cached = M.wrap4(original, function() return now end)
check(cached(1, 2, 3, 4) == 10 and calls == 1, "first call")
check(cached(1, 2, 3, 4) == 10 and calls == 1, "identical inputs")
for position = 1, 4 do
    local args = {1, 2, 3, 4}; args[position] = args[position] + 1
    local before = calls
    check(cached(unpack(args)) == 11 and calls == before + 1, "changed input " .. position)
end
cached(1, 2, 3, 4)
now = 0.049
local before = calls
cached(1, 2, 3, 4)
check(calls == before, "under 50ms")
now = 0.05; cached(1, 2, 3, 4)
check(calls == before + 1, "50ms expiry")
now = -1; cached(1, 2, 3, 4)
check(calls == before + 2, "clock reset")
now = nil; cached(1, 2, 3, 4); cached(1, 2, 3, 4)
check(calls == before + 4, "invalid clock bypass")
now = 1
cached(1, 2, 3, 4)
throw = true; now = 2
check(not pcall(cached, 1, 2, 3, 4), "original exception propagates")
throw = false
before = calls; cached(1, 2, 3, 4)
check(calls == before + 1, "exception did not cache stale result")
local negatives = M.wrap4(function(a) return 1 / a end, function() return 0 end)
check(negatives(0, 0, 0, 0) == math.huge and negatives(-1/math.huge, 0, 0, 0) == -math.huge, "signed zero")
local nonfinite_calls = 0
local special = M.wrap4(function(a) nonfinite_calls = nonfinite_calls + 1; return a end, function() return 0 end)
special(0/0, 0, 0, 0); special(0/0, 0, 0, 0)
special(math.huge, 0, 0, 0); special(math.huge, 0, 0, 0)
check(nonfinite_calls == 4, "nonfinite inputs bypass")
local nil_calls = 0
local nothing = M.wrap4(function() nil_calls = nil_calls + 1 end, function() return 0 end)
check(nothing(0, 0, 0, 0) == nil and nothing(0, 0, 0, 0) == nil and nil_calls == 2, "nil result not cached")

-- Run the package's exact source anchors, then its real installation blocks.
local f = assert(io.open(root .. "/artifacts/pure-functions.lua")); local bodies = f:read("*a"); f:close()
assert(loadstring(bodies))()
local originals = {nd_calc_dist2, nd_calc_brg}
local wrapped = {M.wrap4(nd_calc_dist2, function() return now end), M.wrap4(nd_calc_brg, function() return now end)}
math.randomseed(737)
for n = 1, 10000 do
    local a, b, c, d = math.random()*180-90, math.random()*360-180, math.random()*180-90, math.random()*360-180
    now = n / 120
    for i = 1, 2 do
        local expected = originals[i](a, b, c, d)
        check(wrapped[i](a, b, c, d) == expected, "exact geometry output")
        check(wrapped[i](a, b, c, d) == expected, "exact cached output")
    end
end
local points = {{0, 0, 0, 0}, {90, 0, -90, 0}, {0, 179.999, 0, -179.999}, {-0.0, 0, 0, -0.0}}
for _, point in ipairs(points) do
    for i = 1, 2 do
        local expected, actual = originals[i](unpack(point)), wrapped[i](unpack(point))
        check(expected == actual or (expected ~= expected and actual ~= actual), "geometry edge")
    end
end
-- Exercise the actual package loader and both installation blocks. The
-- custom XLua dofile intentionally discards returned values.
local real_dofile = dofile
function raw_table(name) rawset(_G, name, nil) end
function find_dataref() return 0 end
function dofile(path)
    real_dofile(root .. "/modules/lua-timer/payload/" .. path)
end
local blocks = assert(io.open(root .. "/artifacts/installation-blocks.lua")):read("*a")
assert(loadstring(blocks))()
check(type(nd_calc_dist2) == "function" and type(nd_calc_brg) == "function", "loader discarding return value")
check(nd_calc_dist2 ~= originals[1] and nd_calc_brg ~= originals[2], "real hooks installed")
for n = 1, 16 do nd_calc_dist2(50, 8, 51 + n / 1000, 9) end
check(nd_calc_dist2 == originals[1], "changing inputs remove unhelpful cache")
local protected_original = function(a) return a end
local active
local protected_cache = M.wrap4(protected_original, function() return now end, function(original, wrapper)
    if active == wrapper then active = original end
end)
active = function() return 999 end
for n = 1, 16 do protected_cache(n, 0, 0, 0) end
check(active() == 999, "disable preserves another later wrapper")
-- A loader failure leaves all original functions intact.
nd_calc_dist2, nd_calc_brg = originals[1], originals[2]
function dofile() error("missing helper") end
assert(loadstring(blocks))()
check(nd_calc_dist2 == originals[1] and nd_calc_brg == originals[2], "missing helper leaves original behaviour")
dofile = real_dofile
for _, fps in ipairs({10, 20, 30, 60, 120}) do
    local elapsed = 0
    for frame = 1, fps * 60 do
        SIM_PERIOD = 1 / fps
        now = frame / fps
        local period = SIM_PERIOD
        wrapped[1](50, 8, 51, 9)
        elapsed = elapsed + SIM_PERIOD
        check(SIM_PERIOD == period, "SIM_PERIOD untouched")
    end
    check(math.abs(elapsed - 60) < 1e-8, "60 seconds at " .. fps .. " FPS")
end
IN_REPLAY, SIM_PERIOD = 1, 0
now = 60
check(wrapped[1](50, 8, 51, 9) == originals[1](50, 8, 51, 9) and IN_REPLAY == 1 and SIM_PERIOD == 0, "pause/replay untouched")

local loops, sink = 300000, 0
now = 0
local function benchmark(fn, changed)
    local start = os.clock()
    for n = 1, loops do sink = sink + fn(50, 8, changed and 51 + n/100000 or 51, 9) end
    return os.clock() - start
end
for i = 1, 2 do
    local stock, hit = benchmark(originals[i], false), benchmark(wrapped[i], false)
    local cold_stock, miss = benchmark(originals[i], true), benchmark(wrapped[i], true)
    print(string.format("BENCH function=%d stock=%.6f repeated=%.6f changing_stock=%.6f changing_cache=%.6f", i, stock, hit, cold_stock, miss))
end
local function adaptive_benchmark(original, changed)
    local active
    active = M.wrap4(original, function() return now end, function(fn, wrapper)
        if active == wrapper then active = fn end
    end)
    local start = os.clock()
    for n = 1, loops do sink = sink + active(50, 8, changed and 51 + n/100000 or 51, 9) end
    return os.clock() - start
end
for i = 1, 2 do
    print(string.format("BENCH adaptive function=%d repeated=%.6f changing=%.6f", i, adaptive_benchmark(originals[i], false), adaptive_benchmark(originals[i], true)))
end
print("PASS runtime assertions=" .. total)
