import luaparser.asttokens
import ast
import re
from antlr4 import *
from luaparser.parser.LuaLexer import LuaLexer
from luaparser.parser.LuaVisitor import LuaVisitor
from luaparser.astnodes import *
from luaparser.parser.LuaParser import LuaParser

def parse(source):
    lexer = LuaLexer(InputStream(source))
    parser = LuaParser(CommonTokenStream(lexer))
    astVisitor = ParseTreeVisitor()
    return astVisitor.visit(parser.chunk())

def _listify(obj):
    if not isinstance(obj, list):
        return [obj]
    else:
        return obj

def _setMetadata(ctx, node):
    if ctx.start:
        node.start = ctx.start.tokenIndex
    if ctx.stop:
        node.stop  = ctx.stop.tokenIndex
    return node

class ParseTreeVisitor(LuaVisitor):
    def visitChildren(self, ctx, mergeList=False):
        if ctx.children:
            return self.visitChildrenList(ctx.children, mergeList)
        else:
            return []

    def visitChildrenList(self, children, mergeList=False):
        nodes = []
        for child in children:
            node = self.visit(child)
            if node != None:
                if mergeList and isinstance(node, list):
                    nodes.extend(node)
                else:
                    nodes.append(node)
        if len(nodes) == 1:
            return nodes[0]
        return nodes

    def visitStartingFrom(self, ctx, index, mergeList=False):
        if ctx.children:
            return self.visitChildrenList(ctx.children[index:], mergeList)
        else:
            return []


    ''' Visiting root nodes.
    '''
    def visitChunk(self, ctx):
        return _setMetadata(ctx, Chunk(self.visit(ctx.children[0])))

    def visitBlock(self, ctx):
        return _setMetadata(ctx, Block(_listify(self.visitChildren(ctx))))

    ''' ----------------------------------------------------------------------- '''
    ''' 3.3 – Statements                                                        '''
    ''' ----------------------------------------------------------------------- '''
    def visitSetStat(self, ctx):
        return _setMetadata(ctx, Assign(
            targets=_listify(self.visit(ctx.children[0])), \
            values=_listify(self.visit(ctx.children[2]))))

    def visitLocalset(self, ctx):
        # 'local' namelist ('=' explist)?
        if len(ctx.children) > 2:
            return _setMetadata(ctx, LocalAssign(
                targets=_listify(self.visit(ctx.children[1])), \
                values=_listify(self.visit(ctx.children[3]))))
        else:
            return _setMetadata(ctx, LocalAssign(
                targets=_listify(self.visit(ctx.children[1])), \
                values=[]))

    def visitWhileStat(self, ctx):
        # 'while' exp 'do' block 'end' ;
        return _setMetadata(ctx, While(
            test=self.visit(ctx.children[1]),
            body=self.visit(ctx.children[3]).body))

    def visitRepeat(self, ctx):
        # 'repeat' block 'until' exp ;
        return _setMetadata(ctx, Repeat(
            body=self.visit(ctx.children[1]).body,
            test=self.visit(ctx.children[3])))

    def visitCall(self, ctx):
        # varOrExp args+

        return _setMetadata(ctx, Call(
            func=self.visit(ctx.children[0]), \
            args=_listify(self.visitStartingFrom(ctx, 1))))

    def visitInvoke(self, ctx):
        # varOrExp (':' name args)+
        child = Invoke(
            source=self.visit(ctx.children[0]), \
            func=self.visit(ctx.children[2]), \
            args=_listify(self.visit(ctx.children[3])))
        # if nested invoke:
        if len(ctx.children)>4:
            # iterate (':' name args)
            for i in range(4, len(ctx.children), 3):
                root = Invoke(
                    source=child, \
                    func=self.visit(ctx.children[i+1]), \
                    args=_listify(self.visit(ctx.children[i+2])))
                child = root
            return _setMetadata(ctx, child)
        else:
            return _setMetadata(ctx, child)

    def visitFornum(self, ctx):
        # 'for' name '=' exp ',' exp (',' exp)? 'do' block 'end' ;
        # if has step expr
        if len(ctx.children) > 8:
            return _setMetadata(ctx, Fornum(
                start=self.visit(ctx.children[3]),
                stop=self.visit(ctx.children[5]),
                step=self.visit(ctx.children[7])))
        else:
            return _setMetadata(ctx, Fornum(
                start=self.visit(ctx.children[3]),
                stop=self.visit(ctx.children[5]),
                step=Number(1)))

    def visitForin(self, ctx):
        # 'for' namelist 'in' explist 'do' block 'end' ;
        return _setMetadata(ctx, Forin(
            body=self.visit(ctx.children[5]).body,
            iter=self.visit(ctx.children[3]),
            targets=_listify(self.visit(ctx.children[1]))))

    def visitIfStat(self, ctx):
        # 'if' exp 'then' block elseIfStat* elseStat? 'end' ;
        mainIf = If(
            test=self.visit(ctx.children[1]),
            body=self.visit(ctx.children[3]).body,
            orelse=None)
        lastStat = mainIf
        for node in ctx.children[4:-2]:
            elseIfNodes = self.visit(node)
            elseIf = If(test=elseIfNodes[0], body=elseIfNodes[1], orelse=None)
            lastStat.orelse = elseIf
            lastStat = elseIf
        if isinstance(ctx.children[-2], LuaParser.ElseStatContext):
            lastStat.orelse = self.visit(ctx.children[-2])
        return _setMetadata(ctx, mainIf)

    def visitElseIfStat(self, ctx):
        # 'elseif' exp 'then' block
        return [
            self.visit(ctx.children[1]),
            self.visit(ctx.children[3]).body]

    def visitElseStat(self, ctx):
        # 'else' block
        return self.visit(ctx.children[1]).body

    def visitLabel(self, ctx):
        return _setMetadata(ctx, Label(id=self.visit(ctx.children[1]).id))

    def visitGoto(self, ctx):
        return _setMetadata(ctx, Goto(label=self.visit(ctx.children[1]).id))

    def visitBreakStat(self, ctx):
        return _setMetadata(ctx, Break(self.visitChildren(ctx)))

    ''' 
    Visiting expressions.
    '''
    ''' 
    Types and values
    '''
    def visitNil(self, ctx):
        return _setMetadata(ctx, Nil())

    def visitTrue(self, ctx):
        return _setMetadata(ctx, TrueExpr())

    def visitFalse(self, ctx):
        return _setMetadata(ctx, FalseExpr())

    def visitNumber(self, ctx):
        # using python number eval to parse lua number:
        number = ast.literal_eval(ctx.children[0].getText())
        return _setMetadata(ctx, Number(number))

    def visitString(self, ctx):
        luaStr = ctx.children[0].getText()
        p = re.compile('^\[=+\[(.*)\]=+\]') # nested quote pattern
        # try remove double quote:
        if luaStr.startswith('"') and luaStr.endswith('"'):
            luaStr = luaStr[1:-1]
        # try remove single quote:
        elif luaStr.startswith("'") and luaStr.endswith("'"):
            luaStr = luaStr[1:-1]
        # try remove double square bracket:
        elif luaStr.startswith("[[") and luaStr.endswith("]]"):
            luaStr = luaStr[2:-2]
        # nested quote
        elif p.match(luaStr):
            luaStr = p.search(luaStr).group(1)
        return _setMetadata(ctx, String(luaStr))

    def visitName(self, ctx):
        return _setMetadata(ctx, Name(ctx.children[0].getText()))

    def visitArgs(self, ctx):
        return self.visitChildren(ctx, mergeList=True)

    def visitVar(self, ctx):
        # : (name | '(' exp ')' varSuffix) varSuffix*
        # if name varSuffix*
        if len(ctx.children)>1 and isinstance(ctx.children[1], LuaParser.VarSuffixContext):
            child = Index(value=self.visit(ctx.children[0]), idx=self.visit(ctx.children[1]))
            for i in range(2, len(ctx.children)):
                root = Index(value=child, idx=self.visit(ctx.children[i]))
                child = root
            return _setMetadata(ctx, child)
        else:
            return self.visitChildren(ctx)

    '''
    Visiting arithmetic operator expressions
    '''
    def visitOpAdd(self, ctx):
        return _setMetadata(ctx, AddOp(
            left=self.visit(ctx.children[0]), \
            right=self.visit(ctx.children[2])))

    def visitOpSub(self, ctx):
        return _setMetadata(ctx, SubOp(
            left=self.visit(ctx.children[0]), \
            right=self.visit(ctx.children[2])))

    def visitOpMult(self, ctx):
        return _setMetadata(ctx, MultOp(
            left=self.visit(ctx.children[0]), \
            right=self.visit(ctx.children[2])))

    def visitOpFloatDiv(self, ctx):
        return _setMetadata(ctx, FloatDivOp(
            left=self.visit(ctx.children[0]), \
            right=self.visit(ctx.children[2])))

    def visitOpFloorDiv(self, ctx):
        return _setMetadata(ctx, FloorDivOp(
            left=self.visit(ctx.children[0]), \
            right=self.visit(ctx.children[2])))

    def visitOpMod(self, ctx):
        return _setMetadata(ctx, ModOp(
            left=self.visit(ctx.children[0]), \
            right=self.visit(ctx.children[2])))

    def visitOpExpo(self, ctx):
        return _setMetadata(ctx, ExpoOp(
            left=self.visit(ctx.children[0]), \
            right=self.visit(ctx.children[2])))

    def visitOpMin(self, ctx):
        return _setMetadata(ctx, NegOp(self.visitChildren(ctx)))

    '''
    Relational Operators
    '''
    def visitRelOpLess(self, ctx):
        return _setMetadata(ctx, LessThanOp(
            left=self.visit(ctx.children[0]), \
            right=self.visit(ctx.children[2])))

    def visitRelOpGreater(self, ctx):
        return _setMetadata(ctx, GreaterThanOp(
            left=self.visit(ctx.children[0]), \
            right=self.visit(ctx.children[2])))

    def visitRelOpLessEq(self, ctx):
        return _setMetadata(ctx, LessOrEqThanOp(
            left=self.visit(ctx.children[0]), \
            right=self.visit(ctx.children[2])))

    def visitRelOpGreaterEq(self, ctx):
        return _setMetadata(ctx, GreaterOrEqThanOp(
            left=self.visit(ctx.children[0]), \
            right=self.visit(ctx.children[2])))

    def visitRelOpNotEq(self, ctx):
        return _setMetadata(ctx, NotEqToOp(
            left=self.visit(ctx.children[0]), \
            right=self.visit(ctx.children[2])))

    def visitRelOpEq(self, ctx):
        return _setMetadata(ctx, EqToOp(
            left=self.visit(ctx.children[0]), \
            right=self.visit(ctx.children[2])))


    '''
    3.4.2 – Bitwise Operators
    '''
    def visitBitOpAnd(self, ctx):
        return _setMetadata(ctx, BAndOp(
            left=self.visit(ctx.children[0]), \
            right=self.visit(ctx.children[2])))

    def visitBitOpOr(self, ctx):
        return _setMetadata(ctx, BOrOp(
            left=self.visit(ctx.children[0]), \
            right=self.visit(ctx.children[2])))

    def visitBitOpXor(self, ctx):
        return _setMetadata(ctx, BXorOp(
            left=self.visit(ctx.children[0]), \
            right=self.visit(ctx.children[2])))

    def visitBitOpShiftR(self, ctx):
        return _setMetadata(ctx, BShiftROp(
            left=self.visit(ctx.children[0]), \
            right=self.visit(ctx.children[2])))

    def visitBitOpShiftL(self, ctx):
        return _setMetadata(ctx, BShiftLOp(
            left=self.visit(ctx.children[0]), \
            right=self.visit(ctx.children[2])))

    '''
    Unary Operators
    '''
    def visitUnOpMin(self, ctx):
        return _setMetadata(ctx, USubOp(operand=self.visit(ctx.children[1])))

    def visitUnOpBitNot(self, ctx):
        return _setMetadata(ctx, UBNotOp(operand=self.visit(ctx.children[1])))

    def visitUnOpNot(self, ctx):
        return _setMetadata(ctx, ULNotOp(self.visitChildren(ctx)))

    '''
    3.4.5 – Logical Operators
    '''
    def visitLoOpAnd(self, ctx):
        return _setMetadata(ctx, AndLoOp(
            left=self.visit(ctx.children[0]), \
            right=self.visit(ctx.children[2])))

    def visitLoOpOr(self, ctx):
        return _setMetadata(ctx, OrLoOp(
            left=self.visit(ctx.children[0]), \
            right=self.visit(ctx.children[2])))

    ''' ----------------------------------------------------------------------- '''
    ''' 3.4.6 – Concatenation                                                   '''
    ''' ----------------------------------------------------------------------- '''
    def visitConcat(self, ctx):
        return _setMetadata(ctx, Concat(
            left=self.visit(ctx.children[0]), \
            right=self.visit(ctx.children[2])))

    ''' ----------------------------------------------------------------------- '''
    ''' 3.4.7 – The Length Operator                                             '''
    ''' ----------------------------------------------------------------------- '''
    def visitUnOpLength(self, ctx):
        return _setMetadata(ctx, ULengthOP(operand=self.visit(ctx.children[1])))

    ''' ----------------------------------------------------------------------- '''
    ''' 3.4.9 – Table Constructors                                              '''
    ''' ----------------------------------------------------------------------- '''
    def visitTableconstructor(self, ctx):
        # table      : '{' (field (fieldsep field)* fieldsep?)? '}'
        # field      : '[' tableKey ']' '=' tableValue | tableKey '=' tableValue | tableValue
        # tableKey   : exp | name
        # tableValue : exp
        keys    = []
        values  = []
        index   = 1 # lua array start index
        for field in ctx.children:
            if isinstance(field, LuaParser.FieldContext):
                hasKey = False
                for tblElem in field.children:
                    if isinstance(tblElem, LuaParser.TableKeyContext):
                        keys.append(self.visitChildren(tblElem))
                        hasKey = True
                    elif isinstance(tblElem, LuaParser.TableValueContext):
                        values.append(self.visitChildren(tblElem))
                # if no index found, create an integer key:
                if not hasKey:
                    keys.append(Number(index))
                    index += 1
        return _setMetadata(ctx, Table(keys, values))

    ''' ----------------------------------------------------------------------- '''
    ''' 3.4.11 – Function Definitions                                           '''
    ''' ----------------------------------------------------------------------- '''
    def visitFunctiondef(self, ctx):
        # 'function' funcbody
        argsBlock = self.visit(ctx.children[1])
        return _setMetadata(ctx, Function(name='', args=argsBlock[0], body=argsBlock[1].body))

    def visitFuncbody(self, ctx):
        # '(' parlist? ')' block 'end'
        if isinstance(ctx.children[1], LuaParser.ParlistContext):
            nodes = [self.visit(ctx.children[1]),
                     self.visit(ctx.children[3])]
        else:
            nodes = [[],self.visit(ctx.children[2])]
        return nodes

    def visitParlist(self, ctx):
        return self.visitChildren(ctx, True)

    def visitFunc(self, ctx):
        # 'function' funcname funcbody
        name      = self.visit(ctx.children[1])
        argsBlock = self.visit(ctx.children[2])

        if isinstance(name, Name):
            return _setMetadata(ctx, Function(name=name.id, args=argsBlock[0], body=argsBlock[1].body))
        else:
            return _setMetadata(ctx, Assign(
                targets=[name],
                values =[Function(name='', args=argsBlock[0], body=argsBlock[1].body)]))

    def visitLocalfunc(self, ctx):
        # 'local' 'function' name funcbody
        name      = self.visit(ctx.children[2])
        argsBlock = self.visit(ctx.children[3])
        return _setMetadata(ctx, LocalFunction(name=name.id, args=argsBlock[0], body=argsBlock[1].body))


    def visitFuncname(self, ctx):
        # name ('.' name)* (':' name)?
        if len(ctx.children)>2:
            child = Index(value=self.visit(ctx.children[0]), idx=self.visit(ctx.children[2]).id)

            for i in range(3, len(ctx.children)):
                if isinstance(ctx.children[i], LuaParser.NameContext):
                    root = Index(value=child, idx=self.visit(ctx.children[i]).id)
                    child = root
            return _setMetadata(ctx, child)
        else:
            return self.visitChildren(ctx)


    ''' ----------------------------------------------------------------------- '''
    ''' Comments                                                                '''
    ''' ----------------------------------------------------------------------- '''
    def visitComment_rule(self, ctx):
        comment = self.visitString(ctx).s
        if comment.startswith('--'):
            comment = comment[2:]
        return _setMetadata(ctx, Comment(comment.strip(' \t\n\r')))

class ASTVisitor():
    def do_visit(self, node):
        if isinstance(node, Node):
            name = 'visit_' + node.__class__.__name__
            visitor = getattr(self, name, None)
            if visitor:
                visitor(node)
            # visit all object public attributes:
            childs = [attr for attr in node.__dict__.keys() if not attr.startswith("_")]
            for child in childs:
                self.visit(node.__dict__[child])

    def visit(self, node):
        if isinstance(node, list):
            for n in node:
                self.do_visit(n)
        else:
            self.do_visit(node)