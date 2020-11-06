from luaparser import ast
from luaparser import astnodes

a = ""
with open("test_kernels.lua", "r") as f:
    a = f.read()


tree, builder = ast.parse(a)
print(ast.to_c_str(tree))
#print(ast.to_lua_str(tree))
