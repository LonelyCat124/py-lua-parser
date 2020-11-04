"""
    ``printers`` module
    ===================

    Contains utilities to render an ast tree to text or html.
"""

from luaparser.astnodes import *
from luaparser.utils.visitor import *
from enum import Enum
import xml.etree.cElementTree as ElementTree
from xml.dom import minidom

class WrongNumberOfArgsError(Exception):
    pass

class IllegalInvokeError(Exception):
    pass

class UnknownKernelType(Exception):
    pass

class Style(Enum):
    PYTHON = 1
    HTML = 2
    REGENT = 3


###FIXME CURRENTLY NO INDENTATION OR DIFFERENTIATION BETWEEN REGENT AND LUA CODE SECTIONS
class RegentStyleVisitor:
    def __init__(self, indent):
        self.indentValue = indent
        self.currentIndent = 0
        self.currentArgs = {}
        self.inRegent = False

    @visitor(str)
    def visit(self, node):
        return node.strip()

    @visitor(float)
    def visit(self, node):
        return str(node)

    @visitor(int)
    def visit(self, node):
        return str(node)

    def indent_str(self, newLine=True):
        res = ' ' * self.currentIndent
        if newLine:
            res = '\n' + res
        return res

    def indent(self):
        self.currentIndent += self.indentValue

    def dedent(self):
        self.currentIndent -= self.indentValue

    def enter_regent(self):
        self.inRegent = True

    def in_regent(self):
        return self.inRegent

    def leave_regent(self):
        self.inRegent = False

    @visitor(list)
    def visit(self, obj):
        res = ''
        k = 0
        for itemValue in obj:
            if type(itemValue) == Call:
                res += self.indent_str()
            res += self.visit(itemValue)
        return res


###
### Left-Hand Side Expression
###

    @visitor(Name)
    def visit(self, node):
        return node.id

    @visitor(Index)
    def visit(self, node):
        value = self.visit(node.value)
        string = self.visit(node.idx)
        if string.startswith('"') and string.endswith('"'):
            res = value + '[' + string + ']'
        else:
            res = value + "." + string
        return res

###
### Statements
###
    @visitor(Assign)
    def visit(self, node):
        res = ""
        res += self.indent_str()
        multiple_child = False
        for child in node.targets:
            if multiple_child:
                res += ", "
            res += self.visit(child)
            multiple_child = True
        res += " = "
        multiple_child = False
        for child in node.values:
            if multiple_child:
                res += ", "
            res += self.visit(child)
            multiple_child = True
        #In regent blocks we end things in blocks with a ;
        if self.in_regent():
            res += ";"
        return res

    @visitor(LocalAssign)
    def visit(self, node):
        if self.in_regent():
            res = self.indent_str() + "var "
        else:
            res =  self.indent_str() + "local "
        multiple_child = False
        for child in node.targets:
            if multiple_child:
                res += ", "
            res += self.visit(child)
            multiple_child = True
        res += " = "
        multiple_child = False
        for child in node.values:
            if multiple_child:
                res += ", "
            res += self.visit(child)
            multiple_child = True
        #In regent blocks we end things in blocks with a ;
        if self.in_regent():
            res += ";"
        return res

    @visitor(While)
    def visit(self, node):
        res = self.indent_str()
        res += "while " + self.visit(node.test) + " do"
        self.indent()
        res += self.visit(node.body)
        self.dedent()
        res+= self.indent_str() + "end"
        return res

    @visitor(Do)
    def visit(self, node):
        res = "do"
        self.indent()
        res += self.visit(node.body)
        seld.dedent()
        res += self.indent_str() + "end"
        return res

    @visitor(Repeat)
    def visit(self, node):
        res = "repeat"
        self.indent()
        res += self.visit(node.body)
        self.dedent()
        res += self.indent_str() + "until" + self.visit(node.test) + "\n"
        return res

    @visitor(ElseIf)
    def visit(self, node):
        res = self.indent_str() + "elseif " + self.visit(node.test) + " then"
        self.indent()
        res += self.visit(node.body)
        self.dedent()
        if node.orelse != None:
            res += self.visit(node.orelse)
        return res

    @visitor(If)
    def visit(self, node):
        res = self.indent_str() + "if " + self.visit(node.test) + " then"
        self.indent()
        res += self.visit(node.body)
        self.dedent()
        if node.orelse != None:
            res += self.visit(node.orelse)
        res += self.indent_str() + "end"
        return res

    @visitor(Label)
    def visit(self, node):
        res = self.indent_str() +  "::"+self.visit(node.id)+"::"
        return res

    @visitor(Goto)
    def visit(self, node):
        print("WARNING GOTO STATEMENT DETECTED. THIS IS NOT RECOMMENDED")
        res = self.indent_str() + "goto " + self.visit(node.label)
        return res

    @visitor(SemiColon)
    def visit(self, node):
        res = ";"
        return res

    @visitor(Break)
    def visit(self, node):
        res = self.indent_str() + "break"
        return res

    @visitor(Return)
    def visit(self, node):
        res = self.indent_str() + "return " + self.visit(node.values)
        return res

    @visitor(Fornum)
    def visit(self, node):
        ##Step is always part of the AST
        res = self.indent_str() + "for " + self.visit(node.target)+ " = " + self.visit(node.start) + " , " + self.visit(node.stop) + " , " + self.visit(node.step) + " do"
        self.indent()
        res += self.visit(node.body)
        self.dedent()
        res += self.indent_str() + "end"
        return res

    @visitor(Forin)
    def visit(self, node):
        res = self.indent_str() + "for "
        multiple_targets = False
        for child in node.targets:
            if multiple_targets:
                res += " , "
            res += self.visit(child)
            multiple_targets = True
        res += " in "
        multiple_expr = False
        for child in node.iter:
            if multiple_expr:
                res += " , "
            res += self.visit(child)
            multiple_expr = True
        self.indent()
        res += self.visit(node.body)
        self.dedent()
        return res

    @visitor(Call)
    def visit(self, node):
        res = self.visit(node.func)
        res += "( "
        multiple_args = False
        for child in node.args:
            if multiple_args:
                res += " , "
            res += self.visit(child)
            multiple_args = True
        res += " )"
        #In regent blocks we end things in blocks with a ;
        if self.in_regent():
            res += ";"
        return res

    @visitor(Invoke)
    def visit(self, node):
        res = self.indent_str() + self.visit(node.source)
        res += ":"
        res += self.visit(node.func)
        res += "( "
        multiple_args = False
        for child in node.args:
            if multiple_args:
                res += " , "
            res += self.visit(child)
            multiple_args = True
        res += " )"
        #In regent blocks we end things in blocks with a ;
        if self.in_regent():
            res += ";"
        return res

    @visitor(Function)
    def visit(self, node):
        res = self.indent_str() + "function "
        res += self.visit(node.name)
        res += "( "
        multiple_args = False
        for child in node.args:
            if multiple_args:
                res += " , "
            res += self.visit(child)
            multiple_args = True
        res += " )"
        self.indent()
        res += self.visit(node.body)
        self.dedent()
        res += self.indent_str() + "end\n"
        return res
    
    @visitor(DSL_main)
    def visit(self, node):
        self.enter_regent()
        res = self.indent_str() + "task main()"
        res += self.indent_str() + "[simple_hdf5_module.initialisation( input_file, hdf5_read_mapper, variables, x_cell, y_cell, z_cell)];\n"
        res += self.indent_str() + "[neighbour_init.initialise(variables)];\n"
        res += self.indent_str() + "[neighbour_init.update_cells(variables)];\n"
        self.indent()
        res += self.visit(node.body)
        self.dedent()
        res += self.indent_str() + "end\n"
        self.leave_regent()
        return res

    @visitor(DSL_invoke)
    def visit(self, node):
        if not self.in_regent():
            print("Attempted to call DSL_invoke outside of DSL code")
            raise IllegalInvokeError
        res = self.indent_str()
        args = node.args
        kernel_store = node.kernel_store
        res += "[invoke(variables.config"
        #Deal with args
        for arg in args:
            name = arg.id
            if name in kernel_store.kernels:
                res += ", {" + name + ", PER_PART }"
            elif name in kernel_store.symmetric_kernels:
                res += ", {" + name + ", SYMMETRIC_PAIRWISE }"
            elif name in kernel_store.asymmetric_kernels:
                res += ", {" + name + ", ASYMMETRIC_PAIRWISE }"
            else:
                print("UNKNOWN KERNEL TYPE")
                raise UnknownKernelType

        res += ", NO_BARRIER)];"
        return res

    @visitor(Kernel)
    def visit(self, node):
        self.enter_regent()
        res = self.indent_str() + "function "
        res += self.visit(node.name)
        res += "( "
        multiple_args = False
        args = 0
        for child in node.args:
            if multiple_args:
                res += " , "
            res += self.visit(child)
            multiple_args = True
            args = args + 1
        if args != 2:
            raise WrongNumberOfArgsError()
        res += " )"
        self.indent()
        res += self.indent_str() + "return rquote\n"
        ##We know how many arguments the Kernel should have, so we can explicitly check that here.
        ##We know the format of the body should be a set of statements, followed by end
        self.indent()
        res += self.visit(node.body)
        self.dedent()
        res += "\n" + self.indent_str() + "end\n"
        self.dedent()
        res += self.indent_str() + "end\n"
        self.leave_regent()
        return res



    @visitor(Symmetric_Pairwise_Kernel)
    def visit(self, node):
        self.enter_regent()
        res = self.indent_str() + "function "
        res += self.visit(node.name)
        res += "( "
        multiple_args = False
        args = 0
        for child in node.args:
            if multiple_args:
                res += " , "
            res += self.visit(child)
            multiple_args = True
            args = args + 1
        if args != 3:
            raise WrongNumberOfArgsError()
        res += " )"
        self.indent()
        res += self.indent_str() + "return rquote\n"
        ##We know how many arguments the Kernel should have, so we can explicitly check that here.
        ##We know the format of the body should be a set of statements, followed by end
        self.indent()
        res += self.visit(node.body)
        self.dedent()
        res += "\n" + self.indent_str() + "end\n"
        self.dedent()
        res += self.indent_str() + "end\n"
        self.leave_regent()
        return res

    @visitor(Asymmetric_Pairwise_Kernel)
    def visit(self, node):
        self.enter_regent()
        res = self.indent_str() + "function "
        res += self.visit(node.name)
        res += "( "
        multiple_args = False
        args = 0
        for child in node.args:
            if multiple_args:
                res += " , "
            res += self.visit(child)
            multiple_args = True
            args = args + 1
        if args != 3:
            raise WrongNumberOfArgsError()
        res += " )"
        self.indent()
        res += self.indent_str() + "return rquote\n"
        ##We know how many arguments the Kernel should have, so we can explicitly check that here.
        ##We know the format of the body should be a set of statements, followed by end
        self.indent()
        res += self.visit(node.body)
        self.dedent()
        res += "\n" + self.indent_str() + "end\n"
        self.dedent()
        res += self.indent_str() + "end\n"
        self.leave_regent()
        return res

    @visitor(Particle_Type)
    def visit(self, node):
        #We only print the particle type in advance
        if node.printed:
            return ""
        res = self.indent_str() + "fspace part {"
        self.indent()
        res += self.indent_str() + "core_part_space : core_part,"
        res += self.indent_str() + "neighbour_part_space : neighbour_part,"
        res += self.visit(node.fspaces)
        self.dedent()
        res += self.indent_str() + "}\n"
        #We now printed this so mark it
        node.printed = True
        return res

    @visitor(LocalFunction)
    def visit(self, node):
        res = self.indent_str() + "local function "
        res += self.visit(node.name)
        res += "( "
        multiple_args = False
        for child in node.args:
            if multiple_args:
                res += " , "
            res += self.visit(child)
            multiple_args = True
        res += " )"
        self.indent()
        res += self.visit(node.body)
        self.dedent()
        res += self.indent_str() + "end"
        return res

    @visitor(Method)
    def visit(self, node):
        res = self.indent_str() + "function "
        res += self.visit(node.source)+"."
        res += self.visit(node.name)
        res += "( "
        multiple_args = False
        for child in node.args:
            if multiple_args:
                res += " , "
            res += self.visit(child)
            multiple_args = True
        res += " )"
        self.indent()
        res += self.visit(node.body)
        self.dedent()
        res += self.indent_str() + "end"
        return res

    @visitor(Statement)
    def visit(self, node):
        print(f"Found unknown statement type: {type(node)}")
        raise NotImplementedError()
###
### Expressions
###
    @visitor(TrueExpr)
    def visit(self, node):
        res = " true "
        return res

    @visitor(FalseExpr)
    def visit(self, node):
        res = " false "
        return res

    @visitor(Number)
    def visit(self, node):
        return self.visit(node.n)

    @visitor(Varargs)
    def visit(self, node):
        res = "..."
        return res

    @visitor(String)
    def visit(self, node):
        res = self.visit(node.s)
        return res

    @visitor(Field)
    def visit(self, node):
        res = ""
        if node.between_brackets:
            print("WARNING - AST found a Field with between_brackets true - this may not generate correct code")
        res = self.visit(node.value)
        return res

    @visitor(Table)
    def visit(self, node):
        if len(node.fields) == 0:
            res = "{}"
        else:
            res = "{"
            multiple_args = False
            for field in node.fields:
                if multiple_args:
                    res += " , "
                res += self.visit(field)
                multiple_args = True
            res += "}"
        return res

    @visitor(Dots)
    def visit(self, node):
        res = "..."
        return res

    @visitor(AnonymousFunction)
    def visit(self, node):
        res = self.indent_str() + "function( "
        multiple_args = False
        for child in node.args:
            if multiple_args:
                res += " , "
            res += self.visit(child)
            multiple_args = True
        res += " )"
        self.indent() 
        res += self.visit(node.body)
        self.dedent()
        res = self.indent_str() + "end"
        return res
        

    @visitor(Comment)
    def visit(self, node):
        ##Is multiline comment
        res = ""
        if node.is_multi_line:
            res = self.indent_str(false) + "--[["
        else:
            res = self.indent_str(false) + "--"
        res += node.s
        if node.is_multi_line:
            res += "\n" + self.indent_str(false) + "--]]\n"




###
### Binary Operators - i.e. A OP B
###

    @visitor(AddOp)
    def visit(self, node):
       res = self.visit(node.left) + " + " + self.visit(node.right)
       return res

    @visitor(SubOp)
    def visit(self, node):
        res = self.visit(node.left) + " - " + self.visit(node.right)
        return res

    @visitor(MultOp)
    def visit(self, node):
        res = self.visit(node.left) + " * " + self.visit(node.right)
        return res

    @visitor(FloatDivOp)
    def visit(self, node):
        res = self.visit(node.left) + " \\ " + self.visit(node.right)
        return res

    @visitor(FloorDivOp)
    def visit(self, node):
        res = self.visit(node.left) + " \\\\" + self.visit(node.right)
        return res

    @visitor(ModOp)
    def visit(self, node):
        res = self.visit(node.left) + " % " + self.visit(node.right)
        return res

    @visitor(ExpoOp)
    def visit(self, node):
        res = self.visit(node.left) + " ^ " + self.visit(node.right)
        return res

    @visitor(BAndOp)
    def visit(self, node):
        res = self.visit(node.left) + " & " + self.visit(node.right)
        return res

    @visitor(BOrOp)
    def visit(self, node):
        res = self.visit(node.left) + " | " + self.visit(node.right)
        return res

    @visitor(BXorOp)
    def visit(self, node):
        res = self.visit(node.left) + " ~ " + self.visit(node.right)
        return res

    @visitor(BShiftROp)
    def visit(self, node):
        res = self.visit(node.left) + " >> " + self.visit(node.right)
        return res

    @visitor(BShiftLOp)
    def visit(self, node):
        res = self.visit(node.left) + " << " + self.visit(node.right)
        return res

    @visitor(LessThanOp)
    def visit(self, node):
        res = self.visit(node.left) + " < " + self.visit(node.right)
        return res

    @visitor(GreaterThanOp)
    def visit(self, node):
        res = self.visit(node.left) + " > " + self.visit(node.right)
        return res

    @visitor(LessOrEqThanOp)
    def visit(self, node):
        res = self.visit(node.left) + " <= " + self.visit(node.right)
        return res

    @visitor(GreaterOrEqThanOp)
    def visit(self, node):
        res = self.visit(node.left) + " >= " + self.visit(node.right)
        return res

    @visitor(EqToOp)
    def visit(self, node):
        res = self.visit(node.left) + " == " + self.visit(node.right)
        return res

    @visitor(NotEqToOp)
    def visit(self, node):
        res = self.visit(node.left) + " ~= " + self.visit(node.right)
        return res

    @visitor(AndLoOp)
    def visit(self, node):
        res = self.visit(node.left) + " and " + self.visit(node.right)
        return res

    @visitor(OrLoOp)
    def visit(self, node):
        res = self.visit(node.left) + " or " + self.visit(node.right)
        return res

    @visitor(Concat)
    def visit(self, node):
        res = self.visit(node.left) + ".." + self.visit(node.right)
        return res

    @visitor(BinaryOp)
    def visit(self, node):
        print(f"{type(node)} Not implemented in Regent codegen")
        raise NotImplementedError()

###
### Unary Operators
###
    @visitor(UMinusOp)
    def visit(self, node):
        res = " -"+self.visit(node.operand)
        return res

    @visitor(UBNotOp)
    def visit(self, node):
        res = " ~" + self.visit(node.operand)
        return res

    @visitor(ULNotOp)
    def visit(self, node):
        res = " not " + self.visit(node.operand)
        return res
###
### Length Operator
###
    @visitor(ULengthOP)
    def visit(self, node):
        res = " #" + self.visit(node.operand)
        return res

    @visitor(UnaryOp)
    def visit(self, node):
        print(f"{type(node)} Not implemented in Regent codegen")
        raise NotImplementedError()

###
### Unknown Operator
###
    @visitor(Op)
    def visit(self, node):
        print(f"{type(node)} Not implemented in Regent codegen")
        raise NotImplementedError()

### Nodes required for particle type declaration
    @visitor(RegentType)
    def visit(self, node):
        return " " + node.type_name

    @visitor(Fspace)
    def visit(self, node):
        res = self.indent_str()
        res += node.name + " :"
        res += self.visit(node.regent_type) + ","
        return res




## Block/Chunk which just recurse.
    @visitor(Node)
    def visit(self, node):
        res = ""
        comments = node.comments
        if comments:
            for c in comments:
                res += self.visit(c)

        for attr, attrValue in node.__dict__.items():
            if not attr.startswith(('_', 'comments')):
                if isinstance(attrValue, Node) or isinstance(attrValue, list):
                    res += self.visit(attrValue)
        return res


class PythonStyleVisitor:
    def __init__(self, indent):
        self.indentValue = indent
        self.currentIndent = 0

    @visitor(str)
    def visit(self, node):
        return repr(node)

    @visitor(float)
    def visit(self, node):
        return str(node)

    @visitor(int)
    def visit(self, node):
        return str(node)

    def indent_str(self, newLine=True):
        res = ' ' * self.currentIndent
        if newLine:
            res = '\n' + res
        return res

    def indent(self):
        self.currentIndent += self.indentValue

    def dedent(self):
        self.currentIndent -= self.indentValue

    @staticmethod
    def pretty_count(node, is_list=False):
        res = ''
        if isinstance(node, list):
            item_count = len(node)
            res += '[] ' + str(item_count) + ' '
            if item_count > 1:
                res += 'items'
            else:
                res += 'item'
        elif isinstance(node, Node):
            if is_list:
                return '{} 1 key'
            key_count = len([attr for attr in node.__dict__.keys() if not attr.startswith("_")])
            res += '{} ' + str(key_count) + ' '
            if key_count > 1:
                res += 'keys'
            else:
                res += 'key'
        else:
            res += '[unknow]'
        return res

    @visitor(list)
    def visit(self, obj):
        res = ''
        k = 0
        for itemValue in obj:
            res += self.indent_str() + str(k) + ': ' + self.pretty_count(itemValue, True)
            self.indent()
            res += self.indent_str(False) + self.visit(itemValue)
            self.dedent()
            k += 1
        return res

    @visitor(Node)
    def visit(self, node):
        res = self.indent_str() + node.display_name + ': ' + self.pretty_count(node)

        self.indent()

        # comments
        comments = node.comments
        if comments:
            res += self.indent_str() + 'comments' + ': ' + self.pretty_count(comments)
            k = 0
            self.indent()
            for c in comments:
                res += self.indent_str() + str(k) + ': ' + self.visit(c.s)
                k += 1
            self.dedent()

        for attr, attrValue in node.__dict__.items():
            if not attr.startswith(('_', 'comments')):
                if isinstance(attrValue, Node) or isinstance(attrValue, list):
                    res += self.indent_str() + attr + ': ' + self.pretty_count(attrValue)
                    self.indent()
                    res += self.visit(attrValue)
                    self.dedent()
                else:
                    if attrValue is not None:
                        res += self.indent_str() + attr + ': ' + self.visit(attrValue)
        self.dedent()
        return res


escape_dict = {
    '\a': r'\a',
    '\b': r'\b',
    '\c': r'\c',
    '\f': r'\f',
    '\n': r'\n',
    '\r': r'\r',
    '\t': r'\t',
    '\v': r'\v',
    '\'': r'\'',
    '\"': r'\"',
    '\0': r'\0',
    '\1': r'\1',
    '\2': r'\2',
    '\3': r'\3',
    '\4': r'\4',
    '\5': r'\5',
    '\6': r'\6',
    '\7': r'\7',
    '\8': r'\8',
    '\9': r'\9'
}


def raw(text):
    """Returns a raw string representation of text"""
    new_string = ''
    for char in text:
        try:
            new_string += escape_dict[char]
        except KeyError:
            new_string += char
    return new_string


class HTMLStyleVisitor:
    def __init__(self):
        pass

    def get_xml_string(self, tree):
        xml = self.visit(tree)

        ast = ElementTree.Element("ast")
        doc = ElementTree.SubElement(ast, "doc")
        doc.append(xml)

        return minidom.parseString(ElementTree.tostring(doc)).toprettyxml(indent="   ")

    @visitor(str)
    def visit(self, node):
        if node.startswith('"') and node.endswith('"'):
            node = node[1:-1]
        return node

    @visitor(float)
    def visit(self, node):
        return str(node)

    @visitor(int)
    def visit(self, node):
        return str(node)

    @visitor(list)
    def visit(self, obj):
        xml_nodes = []
        for itemValue in obj:
            xml_nodes.append(self.visit(itemValue))
        return xml_nodes

    @visitor(Node)
    def visit(self, node):
        xml_node = ElementTree.Element(node.display_name)

        # attributes
        for attr, attrValue in node.__dict__.items():
            if not attr.startswith('_') and attrValue is not None:
                xml_attr = ElementTree.SubElement(xml_node, attr)
                child_node = self.visit(attrValue)
                if type(child_node) is str:
                    xml_attr.text = child_node
                elif type(child_node) is list:
                    xml_attr.extend(child_node)
                else:
                    xml_attr.append(child_node)

        return xml_node
