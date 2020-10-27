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
            #res += self.indent_str() + str(k) + ': ' + self.pretty_count(itemValue, True)
            #self.indent()
            res += self.visit(itemValue)
            #self.dedent()
            #k += 1
        return res


###
### Left-Hand Side Expression
###

    @visitor(Name)
    def visit(self, node):
        return node.id

    @visitor(Index)
    def visit(self, node):
        res = self.visit(node.value)+"."+self.visit(node.idx)
#        res = self.visit(node.idx) + self.visit(node.value)
#        print("INDEX: " + res)
#        print(type(node.idx))
#        print(type(node.value))
        return res

###
### Statements
###
    @visitor(Assign)
    def visit(self, node):
        res = ""
        #print("ASSIGN")
        assert (len(node.targets)) == (len(node.values))
        for child in node.targets:
        #    print(type(child))
            res += self.visit(child)
        res += " = "
        for child in node.values:
        #    print(type(child))
            res += self.visit(child)
        res += "\n"
        return res

    @visitor(LocalAssign)
    def visit(self, node):
        res =  "local "
        #print("LOCALASSIGN")
        assert (len(node.targets)) == (len(node.values))
        for child in node.targets:
        #    print(type(child))
            res += self.visit(child)
        res += " = "
        for a in node.values:
        #    print(type(child))
            res += self.visit(child)
        return res

    @visitor(While)
    def visit(self, node):
        res = "while " + self.visit(node.test)
        res += self.visit(node.body)
        return res

    @visitor(Do)
    def visit(self, node):
        res = " do\n"
        res += self.visit(node.body)
        res += "\nend"
        return res

    @visitor(Repeat)
    def visit(self, node):
        res = "repeat\n"
        res += self.visit(node.body)
        res += "\nuntil" + self.visit(node.test) + "\n"
        return res

    @visitor(ElseIf)
    def visit(self, node):
        res = "elseif " + self.visit(node.test) + " then\n"
        res += self.visit(node.body) + "\n"
        if node.orelse != None:
            res += self.visit(node.orelse)
        return res

    @visitor(If)
    def visit(self, node):
        res = "if " + self.visit(node.test) + " then\n"
        res += self.visit(node.body) + "\n"
        if node.orelse != None:
            res += self.visit(node.orelse)
        res += "end\n"
        return res

    @visitor(Label)
    def visit(self, node):
        res = "::"+self.visit(node.id)+"::"
        return res

    @visitor(Goto)
    def visit(self, node):
        print("WARNING GOTO STATEMENT DETECTED. THIS IS NOT RECOMMENDED")
        res = "goto " + self.visit(node.label)
        return res

    @visitor(SemiColon)
    def visit(self, node):
        res = ";"
        return res

    @visitor(Break)
    def visit(self, node):
        res = "break\n"
        return res

    @visitor(Return)
    def visit(self, node):
        res = "return " + self.visit(node.values)
        return res

    @visitor(Fornum)
    def visit(self, node):
        ##Step is always part of the AST
        res = "for " + self.visit(node.target)+ " = " + self.visit(node.start) + " , " + self.visit(node.stop) + " , " + self.visit(node.step) + " do\n"
        res += self.visit(node.body)
        res += "\nend\n"
        return res

    @visitor(Forin)
    def visit(self, node):
        res = "for "
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
        res += self.visit(node.body)
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
        return res

    @visitor(Invoke)
    def visit(self, node):
        res = self.visit(node.source)
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
        return res

    @visitor(Function)
    def visit(self, node):
        res = "function "
        res += self.visit(node.name)
        res += "( "
        multiple_args = False
        for child in node.args:
            if multiple_args:
                res += " , "
            res += self.visit(child)
            multiple_args = True
        res += " )"
        res += "\n"
        res += self.visit(node.body)
        res += "end"
        return res
        
    ##FIXME - Not implemented correctly yet - put a warning
    @visitor(Kernel)
    def visit(self, node):
        res = "function "
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
        res += "\n"
        res += "return rexpr\n\n"
        ##We know how many arguments the Kernel should have, so we can explicitly check that here.
        ##We know the format of the body should be a set of statements, followed by end
        ##We need to add
        ## return rexpr
        ## .... code here
        ## end
        res += self.visit(node.body)
        res += "end\n\n"
        res += "end\n"
        return res



    ##FIXME - Not implemented correctly yet - put a warning
    @visitor(Symmetric_Pairwise_Kernel)
    def visit(self, node):
        res = "function "
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
        res += "\n"
        res += "return rexpr\n\n"
        ##We know how many arguments the Kernel should have, so we can explicitly check that here.
        ##We know the format of the body should be a set of statements, followed by end
        ##We need to add
        ## return rexpr
        ## .... code here
        ## end
        res += self.visit(node.body)
        res += "end\n\n"
        res += "end\n"
        return res

    @visitor(Asymmetric_Pairwise_Kernel)
    def visit(self, node):
        res = "function "
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
        res += "\n"
        res += "return rexpr\n\n"
        ##We know how many arguments the Kernel should have, so we can explicitly check that here.
        ##We know the format of the body should be a set of statements, followed by end
        ##We need to add
        ## return rexpr
        ## .... code here
        ## end
        res += self.visit(node.body)
        res += "end\n\n"
        res += "end\n"
        return res

    @visitor(LocalFunction)
    def visit(self, node):
        res = "local function "
        res += self.visit(node.name)
        res += "( "
        multiple_args = False
        for child in node.args:
            if multiple_args:
                res += " , "
            res += self.visit(child)
            multiple_args = True
        res += " )"
        res += "\n"
        res += self.visit(node.body)
        res += "end"
        return res

    @visitor(Method)
    def visit(self, node):
        res = "function "
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
        res += "\n"
        res += self.visit(node.body)
        res += "end"
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
        print("Need to see what this is to be able to generate it")
        raise NotImplementedError()

    @visitor(Table)
    def visit(self, node):
        print("Need to see what this is to be able to generate it")
        raise NotImplementedError()

    @visitor(Dots)
    def visit(self, node):
        res = "..."
        return res

    @visitor(AnonymousFunction)
    def visit(self, node):
        res = "function( "
        multiple_args = False
        for child in node.args:
            if multiple_args:
                res += " , "
            res += self.visit(child)
            multiple_args = True
        res += " )"
        res += self.visit(node.body)
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




##FIXME: Eventually this should only be used for things with no "code", e.g.
## Block/Chunk which just recurse.
    @visitor(Node)
    def visit(self, node):
        res = ""
#        res = node.to_regent(self.currentIndent)
#        res = node.display_name + "\n"
#        print(node.display_name)
#        print(node.display_name + ": " + node.to_regent(self.currentIndent) + ": " + node.to_regent_post(self.currentIndent))
#        res = self.indent_str() + node.display_name + ': ' + self.pretty_count(node)
#
#        self.indent()
#
#        # comments
        comments = node.comments
        if comments:
#            res += self.indent_str() + 'comments' + ': ' + self.pretty_count(comments)
#            k = 0
#            self.indent()
            for c in comments:
                res += self.visit(c)
#                res += self.indent_str() + str(k) + ': ' + self.visit(c.s)
#                k += 1
#            self.dedent()
#
        for attr, attrValue in node.__dict__.items():
            if not attr.startswith(('_', 'comments')):
                if isinstance(attrValue, Node) or isinstance(attrValue, list):
                    #res += self.indent_str() + attr + ': ' + self.pretty_count(attrValue)
                    self.indent()
                    res += self.visit(attrValue)
                    self.dedent()
                #else:
                #    if attrValue is not None:
                #        res += self.indent_str() + attr + ': ' + self.visit(attrValue)
        #self.dedent()
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
