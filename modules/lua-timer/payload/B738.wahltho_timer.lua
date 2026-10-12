-- Independent, optional calculation cache by wahltho.
-- Never schedule physics callbacks or change SIM_PERIOD / IN_REPLAY.
local M = {}
local age = 0.05

local function finite(value)
    return type(value) == "number" and value == value
        and value ~= math.huge and value ~= -math.huge
end

function M.wrap4(original, clock, disable)
    assert(type(original) == "function" and type(clock) == "function")
    local valid = false
    local misses = 0
    local saved_a, saved_b, saved_c, saved_d, saved_time, saved_result
    local wrapped
    wrapped = function(a, b, c, d)
        if valid and a == saved_a and b == saved_b and c == saved_c and d == saved_d
            -- atan2 distinguishes positive and negative zero.
            and (a ~= 0 or 1 / a == 1 / saved_a) and (b ~= 0 or 1 / b == 1 / saved_b)
            and (c ~= 0 or 1 / c == 1 / saved_c) and (d ~= 0 or 1 / d == 1 / saved_d) then
            local now = clock()
            if type(now) == "number" and now >= saved_time and now - saved_time < age then
                misses = 0
                return saved_result
            end
        end
        -- An exception must not leave an older successful result usable.
        valid = false
        misses = misses + 1
        if disable ~= nil and misses >= 16 then
            -- Moving coordinates usually cannot benefit. Remove our wrapper
            -- rather than impose ongoing cache overhead on those call sites.
            disable(original, wrapped)
            return original(a, b, c, d)
        end
        local result = original(a, b, c, d)
        if finite(result) and finite(a) and finite(b) and finite(c) and finite(d) then
            local now = clock()
            if not finite(now) then return result end
            saved_a, saved_b, saved_c, saved_d = a, b, c, d
            saved_time, saved_result, valid = now, result, true
        end
        return result
    end
    return wrapped
end

-- XLua's custom dofile does not consistently return the chunk's return value.
B738_wahltho_timer_module = M
return M
