from luaparser import ast
from luaparser import astnodes

a = ""
with open("test_kernels.lua", "r") as f:
    a = f.read()


tree, builder = ast.parse(a)
#print(ast.to_lua_str(tree))

output = "import \"regent\"\n"
output += "require(\"src/particles/core_part\")\n"
output += "require(\"src/neighbour_search/cell_pair_tradequeues/import_cell_pair\")\n\n"

for node in ast.walk(tree):
    if type(node) == astnodes.Particle_Type:
        output += ast.to_lua_str(node)

output += "variables = {}\n"
output += "variables.config = regentlib.newsymbol(\"config\")\n"
output += "variables.particle_array = regentlib.newsymbol(\"particle_region\")\n"
output += "require(\"src/config/space\")\n"
output += "require(\"src/config/default_config\")\n"
output += "neighbour_init = require(\"src/neighbour_search/cell_pair_tradequeues/neighbour_init\")\n"
output += "require(\"src/neighbour_search/cell_pair_tradequeues/neighbour_search\")\n"
output += "require(\"src/neighbour_search/cell_pair_tradequeues/cell\")\n"
output += "require(\"src/io_modules/empty_io/initialisation\")\n"

output += ast.to_lua_str(tree)
print(output)
