
part_type{
   name1 : int,
   whatsup : int32,
   test_bool : bool,
   interactions : uint32,
}

sym_pairwise_kernel test_kernel(part1, part2, r2)

part1.interactions = part1.interactions + 1
part2.interactions = part2.interactions + 1
local x = 3 + 2
end

kernel name_kernel( part1, config)
    if part1.core_part_space.cutoff == 2.3 then
    part1.core_part_space.pos_x = 2.534
  end
end

function lua_function(someargs, ...)
  for i=1, select("#", ...) do
    print(select(i, ...))
  end
  local k = "blah"
  local a = {"thing1", "thing2", k, sin(30)}
  a["food"] = "pizza"
  a.also_food = "potato"
  a.long_quote = [[ thing1
                     whoami
                   thing2]]
end

local format = require("std/format")
dsl_main ()

  local timestep = 0.001
  local end_time = 1.0
  local time = 0.0
  while time < end_time do
    dsl_invoke(name_kernel, test_kernel)
    format.println("Hello")
    time = time + timestep
  end
end
