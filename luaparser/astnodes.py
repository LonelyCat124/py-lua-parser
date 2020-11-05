"""
    ``astnodes`` module
    ===================

    Contains all Ast Node definitions, and a declaration for an object that
    can store the names of Kernels
"""
from typing import List, Optional


Comments = Optional[List[str]]

class Kernel_Store:
    def __init__(self):
        self.kernels = {}
        self.asymmetric_kernels = {}
        self.symmetric_kernels = {}

def _equal_dicts(d1, d2, ignore_keys):
    ignored = set(ignore_keys)
    for k1, v1 in d1.items():
        if k1 not in ignored and (k1 not in d2 or d2[k1] != v1):
            return False
    for k2, v2 in d2.items():
        if k2 not in ignored and k2 not in d1:
            return False
    return True


class Node:
    """Base class for AST node.
    """
    def __init__(self, name: str, comments: Comments = None):
        if comments is None:
            comments = []
        else:
            print(f"COMMENTS {comments}")
        self._name: str = name
        self.comments: List[str] = comments
        self.start_char: int = None  # start character offset
        self.stop_char: int = None  # stop character offset

    @property
    def display_name(self) -> str:
        return self._name

    def __eq__(self, other) -> bool:
        if isinstance(self, other.__class__):
            return _equal_dicts(self.__dict__, other.__dict__, ["start_char", "stop_char"])
        return False

    def to_json(self) -> any:
        return {self._name: {k: v for k, v in self.__dict__.items() if not k.startswith('_') and v}}


class Comment(Node):
    def __init__(self, s: str, is_multi_line: bool = False):
        super(Comment, self).__init__('Comment')
        print(f"Created comment: {s}")
        self.s: str = s
        self.is_multi_line: bool = is_multi_line

    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return _equal_dicts(self.__dict__, other.__dict__, [])
        return False


class Statement(Node):
    """Base class for Lua statement.
    """
    pass


class Expression(Node):
    """Define a Lua expression.
    """
    pass

class Definition(Node):
    """Define a Regent definition.
    """
    pass


class Block(Node):
    """Define a Lua Block.
    """

    def __init__(self, body: List[Statement]):
        super(Block, self).__init__('Block')
        self.body: List[Statement] = body


class Chunk(Node):
    """Define a Lua chunk.

    Attributes:
        body (`Block`): Chunk body.
    """

    def __init__(self, body: Block, comments: Comments = None):
        super(Chunk, self).__init__('Chunk', comments)
        self.body = body


'''
Left Hand Side expression.
'''


class Lhs(Expression):
    """Define a Lua Left Hand Side expression.
    """
    pass


class Name(Lhs):
    """Define a Lua name expression.

    Attributes:
        id (`string`): Id.
    """

    def __init__(self, identifier: str):
        super(Name, self).__init__('Name')
        self.id: str = identifier

    def to_regent(self, indent) -> str:
        return " " + self.id + " "

class Index(Lhs):
    """Define a Lua index expression.

    Attributes:
        idx (`Expression`): Index expression.
        value (`string`): Id.
    """

    def __init__(self, idx: Expression, value: Name):
        super(Index, self).__init__('Index')
        self.idx: Name = idx
        self.value: Expression = value


''' ----------------------------------------------------------------------- '''
''' Statements                                                              '''
''' ----------------------------------------------------------------------- '''


class Assign(Statement):
    """Lua global assignment statement.

    Attributes:
        targets (`list<Node>`): List of targets.
        values (`list<Node>`): List of values.

    """
    def __init__(self, targets: List[Node], values: List[Node], comments: Comments = None):
        super(Assign, self).__init__('Assign', comments)
        self.targets: List[Node] = targets
        self.values: List[Node] = values


class LocalAssign(Assign):
    """Lua local assignment statement.

    Attributes:
        targets (`list<Node>`): List of targets.
        values (`list<Node>`): List of values.
    """

    def __init__(self, targets: List[Node], values: List[Node], comments: Comments = None):
        super(LocalAssign, self).__init__(targets, values, comments)
        self._name: str = 'LocalAssign'


class While(Statement):
    """Lua while statement.

    Attributes:
        test (`Node`): Expression to test.
        body (`Block`): List of statements to execute.
    """

    def __init__(self, test: Expression, body: Block):
        super(While, self).__init__('While')
        self.test: Expression = test
        self.body: Block = body


class Do(Statement):
    """Lua do end statement.

    Attributes:
        body (`Block`): List of statements to execute.
    """

    def __init__(self, body: Block):
        super(Do, self).__init__('Do')
        self.body: Block = body


class Repeat(Statement):
    """Lua repeat until statement.

    Attributes:
        test (`Node`): Expression to test.
        body (`Block`): List of statements to execute.
    """

    def __init__(self, body: Block, test: Expression, comments: Comments = None):
        super(Repeat, self).__init__('Repeat', comments)
        self.body: Block = body
        self.test: Expression = test


class ElseIf(Statement):
    """Define the elseif lua statement.

    Attributes:
        test (`Node`): Expression to test.
        body (`list<Statement>`): List of statements to execute if test is true.
        orelse (`list<Statement> or ElseIf`): List of statements or ElseIf if test if false.
    """

    def __init__(self, test: Node, body: Block, orelse):
        super(ElseIf, self).__init__('ElseIf')
        self.test: Node = test
        self.body: Block = body
        self.orelse = orelse


class If(Statement):
    """Lua if statement.

    Attributes:
        test (`Node`): Expression to test.
        body (`Block`): List of statements to execute if test is true.
        orelse (`list<Statement> or ElseIf`): List of statements or ElseIf if test if false.
    """

    def __init__(self, test: Expression, body: Block, orelse: List[Statement] or ElseIf,
                 comments: Comments = None):
        super(If, self).__init__('If', comments)
        self.test: Expression = test
        self.body: Block = body
        self.orelse = orelse


class Label(Statement):
    """Define the label lua statement.

    Attributes:
        id (`Name`): Label name.
    """

    def __init__(self, label_id: Name):
        super(Label, self).__init__('Label')
        self.id: Name = label_id


class Goto(Statement):
    """Define the goto lua statement.

    Attributes:
        label (`Name`): Label node.
    """

    def __init__(self, label: Name, comments: Comments = None):
        super(Goto, self).__init__('Goto', comments)
        self.label: Name = label


class SemiColon(Statement):
    """Define the semi-colon lua statement.
    """

    def __init__(self):
        super(SemiColon, self).__init__('SemiColon')


class Break(Statement):
    """Define the break lua statement.

    """

    def __init__(self):
        super(Break, self).__init__('Break')


class Return(Statement):
    """Define the Lua return statement.

    Attributes:
        values (`list<Expression>`): Values to return.
    """

    def __init__(self, values):
        super(Return, self).__init__('Return')
        self.values = values


class Fornum(Statement):
    """Define the numeric for lua statement.

    Attributes:
        target (`Name`): Target name.
        start (`Expression`): Start index value.
        stop (`Expression`): Stop index value.
        step (`Expression`): Step value.
        body (`Block`): List of statements to execute.
    """

    def __init__(self, target: Name, start: Expression, stop: Expression, step: Expression, body: Block,
                 comments: Comments = None):
        super(Fornum, self).__init__('Fornum', comments)
        self.target: Name = target
        self.start: Expression = start
        self.stop: Expression = stop
        self.step: Expression = step
        self.body: Block = body


class Forin(Statement):
    """Define the for in lua statement.

    Attributes:
        body (`Block`): List of statements to execute.
        iter (`list<Expression>`): Iterable expressions.
        targets (`list<Name>`): Start index value.
    """

    def __init__(self, body: Block, iter: List[Expression], targets: List[Name], comments: Comments = None):
        super(Forin, self).__init__('Forin', comments)
        self.body: Block = body
        self.iter: List[Expression] = iter
        self.targets: List[Name] = targets


class Call(Statement):
    """Define the function call lua statement.

    Attributes:
        func (`Expression`): Function to call.
        args (`list<Expression>`): Function call arguments.
    """

    def __init__(self, func: Expression, args: List[Expression], comments: Comments = None):
        super(Call, self).__init__('Call', comments)
        self.func: Expression = func
        self.args: List[Expression] = args


class Invoke(Statement):
    """Define the invoke function call lua statement (magic syntax with ':').

    Attributes:
        source (`Expression`): Source expression where function is invoked.
        func (`Expression`): Function to call.
        args (`list<Expression>`): Function call arguments.
    """

    def __init__(self, source: Expression, func: Expression, args: List[Expression]):
        super(Invoke, self).__init__('Invoke')
        self.source: Expression = source
        self.func: Expression = func
        self.args: List[Expression] = args


class Function(Statement):
    """Define the Lua function declaration statement.

    Attributes:
        name (`Expression`): Function name.
        args (`list<Expression>`): Function arguments.
        body (`Block`): List of statements to execute.
    """

    def __init__(self, name: Expression, args: List[Expression], body: Block):
        super(Function, self).__init__('Function')
        self.name: Expression = name
        self.args: List[Expression] = args
        self.body: Block = body

class Kernel(Statement):
    """Define the RegentParticleDSL Kernel declaration statement.

	Attributes:
        name (`Expression`): Function name.
        args (`list<Expression>`): Function arguments.
        body (`Block`): List of statements to execute.
    """
    def __init__(self, name: Expression, args: List[Expression], body: Block):
        super(Kernel, self).__init__('Kernel')
        self.name: Expression = name
        self.args: List[Expression] = args
        self.body: Block = body

class Symmetric_Pairwise_Kernel(Statement):
    """Define the RegentParticleDSL Symmetric Pairwise Kernel declaration statement.

	Attributes:
        name (`Expression`): Function name.
        args (`list<Expression>`): Function arguments.
        body (`Block`): List of statements to execute.
    """
    def __init__(self, name: Expression, args: List[Expression], body: Block):
        super(Symmetric_Pairwise_Kernel, self).__init__('Symmetric_Pairwise_Kernel')
        self.name: Expression = name
        self.args: List[Expression] = args
        self.body: Block = body

class Asymmetric_Pairwise_Kernel(Statement):
    """Define the RegentParticleDSL Asymmetric Pairwise Kernel declaration statement.

	Attributes:
        name (`Expression`): Function name.
        args (`list<Expression>`): Function arguments.
        body (`Block`): List of statements to execute.
    """
    def __init__(self, name: Expression, args: List[Expression], body: Block):
        super(Asymmetric_Pairwise_Kernel, self).__init__('Asymmetric_Pairwise_Kernel')
        self.name: Expression = name
        self.args: List[Expression] = args
        self.body: Block = body

class DSL_main(Statement):
    """Define the RegentParticleDSL main entry point.

        Attributes:
        body (`Block`):  List of staements to execute.
    """
    def __init__(self, body : Block):
        super(DSL_main, self).__init__('DSL_main')
        self.body : Block = body

class DSL_invoke(Statement):
    """Define the RegentParticleDSL invoke function.

        Attributes:
        args (`list<Expression>`): Invoke arguments.
        kernel_store (`Kernel_Store`): The Kernel_Store containing the Kernel functions
    """
    def __init__(self, args: List[Expression], kernel_store : Kernel_Store):
        super(DSL_invoke, self).__init__('DSL_invoke')
        self.args : List[Expression] = args
        self.kernel_store : Kernel_Store = kernel_store

class Particle_Type(Statement):
    """Define the RegentParticleDSL Particle Type declaration statement.

       Attributes: 
       fspaces (`list<Definition>`): Field spaces contained inside the type declaration.
    """
    def __init__(self, fspaces: List[Definition]):
        super(Particle_Type, self).__init__('Particle_Type')
        self.fspaces : List[Definition] = fspaces
        self.printed = False

class LocalFunction(Statement):
    """Define the Lua local function declaration statement.

    Attributes:
        name (`Expression`): Function name.
        args (`list<Expression>`): Function arguments.
        body (`list<Statement>`): List of statements to execute.
    """

    def __init__(self, name: Expression, args: List[Expression], body: Block):
        super(LocalFunction, self).__init__('LocalFunction')
        self.name: Expression = name
        self.args: List[Expression] = args
        self.body: Block = body


class Method(Statement):
    """Define the Lua Object Oriented function statement.

    Attributes:
        source (`Expression`): Source expression where method is defined.
        name (`Expression`): Function name.
        args (`list<Expression>`): Function arguments.
        body (`Block`): List of statements to execute.
    """

    def __init__(self, source: Expression, name: Expression, args: List[Expression], body: Block,
                 comments: Comments = None):
        super(Method, self).__init__('Method', comments)
        self.source: Expression = source
        self.name: Expression = name
        self.args: List[Expression] = args
        self.body: Block = body


''' ----------------------------------------------------------------------- '''
''' Lua Expression                                                          '''
''' ----------------------------------------------------------------------- '''

''' ----------------------------------------------------------------------- '''
''' Types and values                                                        '''
''' ----------------------------------------------------------------------- '''


class Nil(Expression):
    """Define the Lua nil expression.
    """

    def __init__(self):
        super(Nil, self).__init__('Nil')


class TrueExpr(Expression):
    """Define the Lua true expression.
    """

    def __init__(self):
        super(TrueExpr, self).__init__('True')


class FalseExpr(Expression):
    """Define the Lua false expression.
    """

    def __init__(self):
        super(FalseExpr, self).__init__('False')


NumberType = int or float


class Number(Expression):
    """Define the Lua number expression.

    Attributes:
        n (`int|float`): Numeric value.
    """
    def __init__(self, n: NumberType):
        super(Number, self).__init__('Number')
        self.n: NumberType = n


class Varargs(Expression):
    """Define the Lua Varargs expression (...).

    """

    def __init__(self):
        super(Varargs, self).__init__('Varargs')


class String(Expression):
    """Define the Lua string expression.

    Attributes:
        s (`string`): String value.
    """

    def __init__(self, s: str):
        super(String, self).__init__('String')
        self.s: str = s


class Field(Expression):
    """Define a lua table field expression

    Attributes:
        key (`Expression`): Key.
        value (`Expression`): Value.
    """

    def __init__(self, key: Expression, value: Expression, comments: Comments = None,
                 between_brackets: bool = False):
        super(Field, self).__init__('Field', comments)
        self.key: Expression = key
        self.value: Expression = value
        self.between_brackets: bool = between_brackets


class Table(Expression):
    """Define the Lua table expression.

    Attributes:
        fields (`list<Field>`): Table fields.
    """

    def __init__(self, fields: List[Field]):
        super(Table, self).__init__('Table')
        self.fields: List[Field] = fields


class Dots(Expression):
    """Define the Lua dots (...) expression.
    """

    def __init__(self):
        super(Dots, self).__init__('Dots')


class AnonymousFunction(Expression):
    """Define the Lua anonymous function expression.

    Attributes:
        args (`list<Expression>`): Function arguments.
        body (`Block`): List of statements to execute.
    """

    def __init__(self, args: List[Expression], body: Block):
        super(AnonymousFunction, self).__init__('AnonymousFunction')
        self.args: List[Expression] = args
        self.body: Block = body


''' ----------------------------------------------------------------------- '''
''' Operators                                                               '''
''' ----------------------------------------------------------------------- '''


class Op(Expression):
    """Base class for Lua operators.
    """
    pass


class BinaryOp(Op):
    """Base class for Lua 'Left Op Right' Operators.

    Attributes:
        left (`Expression`): Left expression.
        right (`Expression`): Right expression.
    """

    def __init__(self, name, left: Expression, right: Expression):
        super(BinaryOp, self).__init__(name)
        self.left: Expression = left
        self.right: Expression = right


''' ----------------------------------------------------------------------- '''
''' 3.4.1 – Arithmetic Operators                                            '''
''' ----------------------------------------------------------------------- '''


class AriOp(BinaryOp):
    """Base class for Arithmetic Operators"""
    pass


class AddOp(AriOp):
    """Add expression.

    Attributes:
        left (`Expression`): Left expression.
        right (`Expression`): Right expression.
    """

    def __init__(self, left: Expression, right: Expression):
        super(AddOp, self).__init__('AddOp', left, right)


class SubOp(AriOp):
    """Substract expression.

    Attributes:
        left (`Expression`): Left expression.
        right (`Expression`): Right expression.
    """

    def __init__(self, left: Expression, right: Expression):
        super(SubOp, self).__init__('SubOp', left, right)


class MultOp(AriOp):
    """Multiplication expression.

    Attributes:
        left (`Expression`): Left expression.
        right (`Expression`): Right expression.
    """

    def __init__(self, left: Expression, right: Expression):
        super(MultOp, self).__init__('MultOp', left, right)


class FloatDivOp(AriOp):
    """Float division expression.

    Attributes:
        left (`Expression`): Left expression.
        right (`Expression`): Right expression.
    """

    def __init__(self, left: Expression, right: Expression):
        super(FloatDivOp, self).__init__('FloatDivOp', left, right)


class FloorDivOp(AriOp):
    """Floor division expression.

    Attributes:
        left (`Expression`): Left expression.
        right (`Expression`): Right expression.
    """

    def __init__(self, left: Expression, right: Expression):
        super(FloorDivOp, self).__init__('FloorDivOp', left, right)


class ModOp(AriOp):
    """Modulo expression.

    Attributes:
        left (`Expression`): Left expression.
        right (`Expression`): Right expression.
    """

    def __init__(self, left: Expression, right: Expression):
        super(ModOp, self).__init__('ModOp', left, right)


class ExpoOp(AriOp):
    """Exponent expression.

    Attributes:
        left (`Expression`): Left expression.
        right (`Expression`): Right expression.
    """

    def __init__(self, left: Expression, right: Expression):
        super(ExpoOp, self).__init__('ExpoOp', left, right)


''' ----------------------------------------------------------------------- '''
''' 3.4.2 – Bitwise Operators                                               '''
''' ----------------------------------------------------------------------- '''


class BitOp(BinaryOp):
    """Base class for bitwise Operators.
    """
    pass


class BAndOp(BitOp):
    """Bitwise and expression.

    Attributes:
        left (`Expression`): Left expression.
        right (`Expression`): Right expression.
    """

    def __init__(self, left: Expression, right: Expression):
        super(BAndOp, self).__init__('BAndOp', left, right)


class BOrOp(BitOp):
    """Bitwise or expression.

    Attributes:
        left (`Expression`): Left expression.
        right (`Expression`): Right expression.
    """

    def __init__(self, left: Expression, right: Expression):
        super(BOrOp, self).__init__('BOrOp', left, right)


class BXorOp(BitOp):
    """Bitwise xor expression.

    Attributes:
        left (`Expression`): Left expression.
        right (`Expression`): Right expression.
    """

    def __init__(self, left: Expression, right: Expression):
        super(BXorOp, self).__init__('BXorOp', left, right)


class BShiftROp(BitOp):
    """Bitwise right shift expression.

    Attributes:
        left (`Expression`): Left expression.
        right (`Expression`): Right expression.
    """

    def __init__(self, left: Expression, right: Expression):
        super(BShiftROp, self).__init__('BShiftROp', left, right)


class BShiftLOp(BitOp):
    """Bitwise left shift expression.

    Attributes:
        left (`Expression`): Left expression.
        right (`Expression`): Right expression.
    """

    def __init__(self, left: Expression, right: Expression):
        super(BShiftLOp, self).__init__('BShiftLOp', left, right)


''' ----------------------------------------------------------------------- '''
''' 3.4.4 – Relational Operators                                            '''
''' ----------------------------------------------------------------------- '''


class RelOp(BinaryOp):
    """Base class for Lua relational operators.
    """
    pass


class LessThanOp(RelOp):
    """Less than expression.

    Attributes:
        left (`Expression`): Left expression.
        right (`Expression`): Right expression.
    """

    def __init__(self, left: Expression, right: Expression):
        super(LessThanOp, self).__init__('RLtOp', left, right)


class GreaterThanOp(RelOp):
    """Greater than expression.

    Attributes:
        left (`Expression`): Left expression.
        right (`Expression`): Right expression.
    """

    def __init__(self, left: Expression, right: Expression):
        super(GreaterThanOp, self).__init__('RGtOp', left, right)


class LessOrEqThanOp(RelOp):
    """Less or equal expression.

    Attributes:
        left (`Expression`): Left expression.
        right (`Expression`): Right expression.
    """

    def __init__(self, left: Expression, right: Expression):
        super(LessOrEqThanOp, self).__init__('RLtEqOp', left, right)


class GreaterOrEqThanOp(RelOp):
    """Greater or equal expression.

    Attributes:
        left (`Expression`): Left expression.
        right (`Expression`): Right expression.
    """

    def __init__(self, left: Expression, right: Expression):
        super(GreaterOrEqThanOp, self).__init__('RGtEqOp', left, right)


class EqToOp(RelOp):
    """Equal to expression.

    Attributes:
        left (`Expression`): Left expression.
        right (`Expression`): Right expression.
    """

    def __init__(self, left: Expression, right: Expression):
        super(EqToOp, self).__init__('REqOp', left, right)


class NotEqToOp(RelOp):
    """Not equal to expression.

    Attributes:
        left (`Expression`): Left expression.
        right (`Expression`): Right expression.
    """

    def __init__(self, left: Expression, right: Expression):
        super(NotEqToOp, self).__init__('RNotEqOp', left, right)


''' ----------------------------------------------------------------------- '''
''' 3.4.5 – Logical Operators                                               '''
''' ----------------------------------------------------------------------- '''


class LoOp(BinaryOp):
    """Base class for logical operators.
    """
    pass


class AndLoOp(LoOp):
    """Logical and expression.

    Attributes:
        left (`Expression`): Left expression.
        right (`Expression`): Right expression.
    """

    def __init__(self, left: Expression, right: Expression):
        super(AndLoOp, self).__init__('LAndOp', left, right)


class OrLoOp(LoOp):
    """Logical or expression.

    Attributes:
        left (`Expression`): Left expression.
        right (`Expression`): Right expression.
    """

    def __init__(self, left: Expression, right: Expression):
        super(OrLoOp, self).__init__('LOrOp', left, right)


''' ----------------------------------------------------------------------- '''
''' 3.4.6 Concat operators                                                  '''
''' ----------------------------------------------------------------------- '''


class Concat(BinaryOp):
    """Concat expression.

    Attributes:
        left (`Expression`): Left expression.
        right (`Expression`): Right expression.
    """

    def __init__(self, left: Expression, right: Expression):
        super(Concat, self).__init__('Concat', left, right)


''' ----------------------------------------------------------------------- '''
''' Unary operators                                                         '''
''' ----------------------------------------------------------------------- '''


class UnaryOp(Expression):
    """Base class for Lua unitary operator.

    Attributes:
        operand (`Expression`): Operand.
    """

    def __init__(self, name: str, operand: Expression):
        super(UnaryOp, self).__init__(name)
        self.operand = operand


class UMinusOp(UnaryOp):
    """Lua minus unitary operator.

    Attributes:
        operand (`Expression`): Operand.
    """

    def __init__(self, operand: Expression):
        super(UMinusOp, self).__init__('UMinusOp', operand)


class UBNotOp(UnaryOp):
    """Lua binary not unitary operator.

    Attributes:
        operand (`Expression`): Operand.
    """

    def __init__(self, operand: Expression):
        super(UBNotOp, self).__init__('UBNotOp', operand)


class ULNotOp(UnaryOp):
    """Logical not operator.

    Attributes:
        operand (`Expression`): Operand.
    """

    def __init__(self, operand: Expression):
        super(ULNotOp, self).__init__('ULNotOp', operand)


''' ----------------------------------------------------------------------- '''
''' 3.4.7 – The Length Operator                                             '''
''' ----------------------------------------------------------------------- '''


class ULengthOP(UnaryOp):
    """Length operator.
    """

    def __init__(self, operand: Expression):
        super(ULengthOP, self).__init__('ULengthOp', operand)


''' ----------------------------------------------------------------------- '''
''' Regent - Fspace declaration                                             '''
''' ----------------------------------------------------------------------- '''
class RegentType(Node):
    """Defines a type of a variable

       Attributes:
       type_name ('String') : The name of the type
    """
    
    def __init__(self, type_name : String):
        super(RegentType, self).__init__('RegentType', type_name)
        self.type_name = type_name

class Fspace(Definition):
    """Defines a variable declaration inside the particle_type

       Attributes:
       name (`Expression`) : The name of the variable
       regent_type (`RegentType`) : The type of the variable
    """
    
    def __init__(self, name: Expression, regent_type: RegentType):
        super(Fspace, self).__init__('Fspace')
        self.name = name
        self.regent_type = regent_type

