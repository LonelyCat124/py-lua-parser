from antlr4 import InputStream, CommonTokenStream
#from luaparser.parser.LuaLexer import LuaLexer
from luaparser.parser.PartDSLLexer import PartDSLLexer as LuaLexer
from luaparser.astnodes import *
from enum import Enum
import ast
import re
from typing import List
from antlr4.Token import Token


class SyntaxException(Exception):
    def __init__(self, user_msg, token=None):
        if token:
            message = '(' + str(token.line) + ',' + str(token.start) + '): Error: ' + user_msg
        else:
            message = 'Error: ' + user_msg
        super().__init__(message)

class MultipleParticleDeclarationException(Exception):
    pass

class MultipleMainDeclarationException(Exception):
    pass

class Expr(Enum):
    OR = 1
    AND = 2
    REL = 3
    CONCAT = 4
    ADD = 5
    MULT = 6
    BITWISE = 7
    UNARY = 8
    POW = 9
    ATOM = 10


class Tokens:
    AND=1
    ASYM_PAIRWISE_KERNEL=2
    BREAK=3
    DO=4
    DSL_MAIN=5
    DSL_INVOKE=6
    ELSETOK=7
    ELSEIF=8
    END=9
    FALSE=10
    FOR=11
    FUNCTION=12
    GOTO=13
    IFTOK=14
    IN=15
    LOCAL=16
    KERNEL=17
    NIL=18
    NOT=19
    OR=20
    PART_TYPE=21
    REPEAT=22
    RETURN=23
    SYM_PAIRWISE_KERNEL=24
    THEN=25
    TRUE=26
    UNTIL=27
    WHILE=28
    ADD=29
    MINUS=30
    MULT=31
    DIV=32
    FLOOR=33
    MOD=34
    POW=35
    LENGTH=36
    EQ=37
    NEQ=38
    LTEQ=39
    GTEQ=40
    LT=41
    GT=42
    ASSIGN=43
    BITAND=44
    BITOR=45
    BITNOT=46
    BITRSHIFT=47
    BITRLEFT=48
    OPAR=49
    CPAR=50
    OBRACE=51
    CBRACE=52
    OBRACK=53
    CBRACK=54
    COLCOL=55
    COL=56
    COMMA=57
    VARARGS=58
    CONCAT=59
    DOT=60
    SEMCOL=61
    INT=62
    UINT=63
    INT32=64
    UINT32=65
    INT64=66
    UINT64=67
    FLOAT=68
    DOUBLE=69
    INT1D=70
    INT2D=71
    INT3D=72
    BOOL=73
    NAME=74
    NUMBER=75
    STRING=76
    COMMENT=77
    LINE_COMMENT=78
    SPACE=79
    NEWLINE=80
    SHEBANG=81
LongBracket=82


#LITERAL_NAMES = ["<INVALID>",
#                 "'and'", "'break'", "'do'", "'else'", "'elseif'", "'end'", "'false'",
#                 "'for'", "'function'", "'goto'", "'if'", "'in'", "'local'",
#                 "'nil'", "'not'", "'or'", "'repeat'", "'return'", "'then'",
#                 "'true'", "'until'", "'while'", "'+'", "'-'", "'*'", "'/'",
#                 "'//'", "'%'", "'^'", "'#'", "'=='", "'~='", "'<='", "'>='",
#                 "'<'", "'>'", "'='", "'&'", "'|'", "'~'", "'>>'", "'<<'", "'('",
#                 "')'", "'{'", "'}'", "'['", "']'", "'::'", "':'", "','", "'...'",
#                 "'..'", "'.'", "';'", "NAME", "NUMBER", "STRING", "COMMENT", "LINE_COMMENT",
#                 "SPACE", "NEWLINE", "SHEBANG", "LONG_BRACKET"]

LITERAL_NAMES = [ "<INVALID>", "'and'", "'asym_pairwise_kernel'", "'break'",
                     "'do'", "'dsl_main'", "'dsl_invoke'", "'else'", "'elseif'", "'end'", "'false'", "'for'",
                     "'function'", "'goto'", "'if'", "'in'", "'local'",
                     "'kernel'", "'nil'", "'not'", "'or'", "'part_type'",
                     "'repeat'", "'return'", "'sym_pairwise_kernel'", "'then'",
                     "'true'", "'until'", "'while'", "'+'", "'-'", "'*'",
                     "'/'", "'//'", "'%'", "'^'", "'#'", "'=='", "'~='",
                     "'<='", "'>='", "'<'", "'>'", "'='", "'&'", "'|'",
                     "'~'", "'>>'", "'<<'", "'('", "')'", "'{'", "'}'",
                     "'['", "']'", "'::'", "':'", "','", "'...'", "'..'",
                     "'.'", "';'", "'int'", "'uint'", "'int32'", "'uint32'",
                     "'int64'", "'uint64'", "'float'", "'double'", "'int1d'",
                     "'int2d'", "'int3d'", "'bool'", "NAME", "NUMBER", "STRING", "COMMENT", "LINE_COMMENT",
                 "SPACE", "NEWLINE", "SHEBANG", "LONG_BRACKET" ]

def _listify(obj):
    if not isinstance(obj, list):
        return [obj]
    else:
        return obj


class Builder:
    CLOSING_TOKEN = [
        Tokens.END,
        Tokens.CBRACE,
        Tokens.CPAR]

    HIDDEN_TOKEN = [
        Tokens.SHEBANG,
        Tokens.LINE_COMMENT,
        Tokens.COMMENT,
        Tokens.NEWLINE,
        Tokens.SPACE,
        -2]

    REL_OPERATORS = [
        Tokens.LT,
        Tokens.GT,
        Tokens.LTEQ,
        Tokens.GTEQ,
        Tokens.NEQ,
        Tokens.EQ]

    def __init__(self, source):
        self._stream = CommonTokenStream(LuaLexer(InputStream(source)))
        # contains a list of CommonTokens
        self._line_count: int = 0
        self._right_index: int = 0
        self._last_expr_type: int = None

        # following stack are used to backup values
        self._index_stack: List[int] = []
        self._right_index_stack: List[int] = []
        self.text: str = ''  # last token text
        self.type: int = -1  # last token type

        # contains expected token in case of invalid input code
        self._expected = []

        # comments waiting to be inserted into ast nodes
        self._comments_index_stack: List[int] = []
        self.comments: List[Comment] = []
        self._hidden_handled: bool = False
        self._hidden_handled_stack: List[bool] = []

        #Kernels
        self._part_type = None
        self._kernels = Kernel_Store()
        self._dsl_main = None


    def process(self) -> Chunk:
        node = self.parse_chunk()
        if not node:
            raise SyntaxException("Expecting a chunk")
        return node

    def save(self):
        # logging.debug('trying ' + inspect.stack()[1][3])
        self._index_stack.append(self._stream.index)
        self._right_index_stack.append(self._right_index)
        self._comments_index_stack.append(len(self.comments))
        self._hidden_handled_stack.append(self._hidden_handled)

    def success(self):
        self._index_stack.pop()
        self._right_index_stack.pop()
        self._comments_index_stack.pop()
        self._hidden_handled_stack.pop()
        return True

    def failure(self):
        self._stream.seek(self._index_stack.pop())
        self._right_index = self._right_index_stack.pop()
        self._hidden_handled = self._hidden_handled_stack.pop()
        n_elem_to_delete = len(self.comments) - self._comments_index_stack.pop()
        if n_elem_to_delete >= 1:
            del self.comments[-n_elem_to_delete:]
        return False

    def failure_save(self):
        self._stream.seek(self._index_stack.pop())
        self._right_index = self._right_index_stack.pop()
        self._hidden_handled = self._hidden_handled_stack.pop()
        n_elem_to_delete = len(self.comments) - self._comments_index_stack.pop()
        if n_elem_to_delete >= 1:
            del self.comments[-n_elem_to_delete:]

        self._index_stack.append(self._stream.index)
        self._right_index_stack.append(self._right_index)
        self._comments_index_stack.append(len(self.comments))
        self._hidden_handled_stack.append(self._hidden_handled)

    def next_is_rc(self, type_to_seek: int, hidden_right: bool = True) -> Optional[Token]:
        token = self._stream.LT(1)
        tok_type: int = token.type
        self._right_index = self._stream.index

        if tok_type == type_to_seek:
            self.text = token.text
            self.type = tok_type
            self._stream.consume()
            self._hidden_handled = False
            if hidden_right:
                self.handle_hidden_right()
            return token
        self._expected.append(type_to_seek)
        return None

    def next_is_c(self, type_to_seek: int, hidden_right: bool = True) -> bool:
        token = self._stream.LT(1)
        tok_type: int = token.type
        self._right_index = self._stream.index

        if tok_type == type_to_seek:
            self._stream.consume()
            self._hidden_handled = False
            if hidden_right:
                self.handle_hidden_right()
            return True
        self._expected.append(type_to_seek)
        return False

    def next_is(self, type_to_seek) -> bool:
        if self._stream.LT(1).type == type_to_seek:
            return True
        else:
            self._expected.append(type_to_seek)
            return False

    def prev_is(self, type_to_seek) -> bool:
        return self._stream.LT(-1).type == type_to_seek

    def next_in_rc(self, types: List[int], hidden_right: bool = True) -> bool:
        token = self._stream.LT(1)
        tok_type: int = token.type
        self._right_index = self._stream.index

        if tok_type in types:
            self.type = tok_type
            self._stream.consume()
            self._hidden_handled = False
            if hidden_right:
                self.handle_hidden_right()
            return True
        self._expected.extend(types)
        return False

    def next_in(self, types: List[int]) -> bool:
        if self._stream.LT(1).type in types:
            return True
        else:
            self._expected.extend(types)
            return False

    def handle_hidden_left(self) -> None:
        tokens = self._stream.getHiddenTokensToLeft(self._stream.index)
        if tokens:
            for t in tokens:
                if not self._hidden_handled:
                    if t.type == Tokens.LINE_COMMENT:
                        self.comments.append(Comment(t.text))
                    elif t.type == Tokens.COMMENT:
                        self.comments.append(Comment(t.text, True))
                    elif t.type == Tokens.NEWLINE:
                        # append n time a None value (indicate newline)
                        self.comments += t.text.count('\n') * [None]

        self._hidden_handled = True

    def handle_hidden_right(self) -> None:
        tokens = self._stream.getHiddenTokensToRight(self._right_index)
        if tokens:
            for t in tokens:
                if not self._hidden_handled:
                    if t.type == Tokens.LINE_COMMENT:
                        self.comments.append(Comment(t.text))
                    elif t.type == Tokens.COMMENT:
                        self.comments.append(Comment(t.text, True))
                    elif t.type == Tokens.NEWLINE:
                        # append n time a None value (indicate newline)
                        self.comments += t.text.count('\n') * [None]

        self._hidden_handled = True

    def get_comments(self) -> Comments:
        comments = [c for c in self.comments if c is not None]
        self.comments = []
        return comments

    def get_comments_followed_by_blank_line(self) -> Comments:
        """ Returns comments followed by a blank line.
        """
        if not self.comments:
            return []

        idx = 0
        comments: List[Comment] = []

        # search first comment
        while idx < len(self.comments) and self.comments[idx] is None:
            idx = idx + 1
        # get comments starting from this index
        while idx < len(self.comments) and self.comments[idx] is not None:
            comments.append(self.comments[idx])
            idx = idx + 1
        # check if followed by a blank line
        if idx + 1 < len(self.comments):
            if self.comments[idx] is None and self.comments[idx + 1] is None:
                # clean list
                self.comments = self.comments[idx + 2:]
                return comments
        return []

    def get_inline_comment(self) -> Comment or None:
        if self.comments:
            c = self.comments.pop(0)
            if c is None:
                return None
            else:
                return c
        return None

    def has_newline_before(self) -> bool:
        return None in self.comments

    def abort(self) -> None:
        types_str = []
        token = self._stream.LT(2)
        expected = set(self._expected)
        for type_to_seek in expected:
            types_str.append(LITERAL_NAMES[type_to_seek])

        raise SyntaxException(
            "Expecting one of " + ', '.join(types_str) + ' at line ' + str(token.line) + ', column ' + str(
                token.column))

    def parse_chunk(self) -> Chunk or None:
        self._stream.LT(1)
        self.handle_hidden_left()
        comments = self.get_comments_followed_by_blank_line()
        block = self.parse_block()
        if block:
            token = self._stream.LT(1)
            if token.type == -1:
                # do not consume EOF
                return Chunk(block, comments)
        return False

    def parse_block(self) -> Block:
        statements = []

        while True:
            stat = self.parse_stat()
            if not stat:
                break
            statements.append(stat)

        # optional ret stat
        stat = self.parse_ret_stat()
        if stat:
            statements.append(stat)
        return Block(statements)

    def parse_stat(self) -> Statement or None:
        comments = self.get_comments()

        stat = \
            self.parse_assignment() or \
            self.parse_var() or \
            self.parse_while_stat() or \
            self.parse_repeat_stat() or \
            self.parse_local() or \
            self.parse_goto_stat() or \
            self.parse_if_stat() or \
            self.parse_for_stat() or \
            self.parse_function() or \
            self.parse_kernel() or \
            self.parse_symmetric_pairwise_kernel() or \
            self.parse_asymmetric_pairwise_kernel() or \
            self.parse_particle_type() or \
            self.parse_dsl_main() or \
            self.parse_dsl_invoke() or \
            self.parse_label()

        if stat:
            stat.comments = comments
            return stat

        stat = self.parse_do_block()
        if stat:
            self.handle_hidden_right()
            return Do(stat)

        if self.next_is(Tokens.BREAK) and self.next_is_rc(Tokens.BREAK):
            self.handle_hidden_right()
            return Break()
        if self.next_is(Tokens.SEMCOL) and self.next_is_rc(Tokens.SEMCOL):
            self.handle_hidden_right()
            return SemiColon()

        return None

    def parse_ret_stat(self) -> Return or bool:
        self.save()
        if self.next_is_rc(Tokens.RETURN):
            expr_list = self.parse_expr_list()  # optional
            # consume optional token
            if self.next_is(Tokens.SEMCOL):
                self.next_is_rc(Tokens.SEMCOL)

            self.success()
            return Return(expr_list)
        return self.failure()

    def parse_assignment(self) -> Assign or bool:
        self.save()
        targets = self.parse_var_list()
        if targets:
            if self.next_is_rc(Tokens.ASSIGN):
                values = self.parse_expr_list()
                if values:
                    self.success()
                    return Assign(targets, values)
                else:
                    self.abort()

        return self.failure()

    def parse_var_list(self) -> List[Expression] or bool:
        lua_vars = []
        self.save()
        var = self.parse_var()
        if var:
            lua_vars.append(var)
            while True:
                self.save()
                if self.next_is_rc(Tokens.COMMA):
                    var = self.parse_var()
                    if var:
                        lua_vars.append(var)
                        self.success()
                    else:
                        self.failure()
                        return self.failure()
                else:
                    self.failure()
                    break
            self.success()
            return lua_vars
        return self.failure()

    def parse_var(self) -> Node or bool:
        root = self.parse_callee()
        if root:
            tail = self.parse_tail()
            while tail:
                if isinstance(tail, Call):
                    tail.func = root
                elif isinstance(tail, Index):
                    tail.value = root
                elif isinstance(tail, Invoke):
                    tail.source = root
                else:
                    tail = Call(root, _listify(tail))
                root = tail

                tail = self.parse_tail()
                if tail:
                    self.handle_hidden_right()

            self.handle_hidden_right()
            return root

        return False

    def parse_tail(self) -> Node or bool:
        # do not render last hidden
        self.save()
        if self.next_is_rc(Tokens.DOT) and self.next_is_rc(Tokens.NAME, False):
            self.success()
            return Index(String(self.text), Name(""))  # value must be set in parent

        self.failure_save()
        if self.next_is_rc(Tokens.OBRACK):
            expr = self.parse_expr()
            if expr and self.next_is_rc(Tokens.CBRACK, False):
                self.success()
                return Index(expr, Name(""))  # value must be set in parent

        self.failure_save()
        if self.next_is_rc(Tokens.COL) and self.next_is_rc(Tokens.NAME):
            name = Name(self.text)
            if self.next_is_rc(Tokens.OPAR):
                expr_list = self.parse_expr_list() or []
                if self.next_is_rc(Tokens.CPAR, False):
                    self.success()
                    # noinspection PyTypeChecker
                    return Invoke(None, name, expr_list)

        self.failure_save()
        if self.next_is_rc(Tokens.COL) and self.next_is_rc(Tokens.NAME):
            name = Name(self.text)
            table = self.parse_table_constructor(False)
            if table:
                self.success()
                # noinspection PyTypeChecker
                return Invoke(None, name, [table])

        self.failure_save()
        if self.next_is_rc(Tokens.COL) and self.next_is_rc(Tokens.NAME):
            name = Name(self.text)
            if self.next_is_rc(Tokens.STRING, False):
                string = self.parse_lua_str(self.text)
                self.success()
                # noinspection PyTypeChecker
                return Invoke(None, name, [string])

        self.failure_save()
        if self.next_is(Tokens.OPAR):
            # handle the ambiguous syntax
            # http://lua-users.org/lists/lua-l/2009-08/msg00543.html
            # example:
            #   a = b + c;
            #   (print or io.write)('foo')

            # check if a newline is present before OPAR
            tokens = self._stream.getHiddenTokensToLeft(self._stream.index)
            if tokens:
                for t in tokens:
                    if t.type == Tokens.NEWLINE and not self.prev_is(Tokens.SEMCOL):
                        raise SyntaxException('Ambiguous syntax detected', self._stream.LT(-1))

        if self.next_is_rc(Tokens.OPAR, False):
            self.handle_hidden_right()
            expr_list = self.parse_expr_list() or []
            if self.next_is_rc(Tokens.CPAR, False):
                self.success()
                # noinspection PyTypeChecker
                return Call(None, expr_list)

        self.failure_save()
        table = self.parse_table_constructor(False)
        if table:
            self.success()
            return table

        self.failure_save()
        if self.next_is_rc(Tokens.STRING, False):
            string = self.parse_lua_str(self.text)
            self.success()
            return string

        return self.failure()

    def parse_expr_list(self) -> List[Expression] or bool:
        expr_list: List[Expression] = []
        self.save()
        expr = self.parse_expr()
        if expr:
            expr_list.append(expr)
            while True:
                self.save()
                if self.next_is_rc(Tokens.COMMA):
                    self._expected = []
                    expr = self.parse_expr()
                    if expr:
                        expr_list.append(expr)
                        self.success()
                    else:
                        # a comma is alone at the end
                        self.failure()
                        self.failure()
                        self.abort()
                else:
                    self.failure()
                    break
            self.success()
            return expr_list
        return self.failure()

    def parse_do_block(self) -> Block or bool:
        self.save()
        if self.next_is_rc(Tokens.DO, False):
            self.handle_hidden_right()
            block = self.parse_block()
            if block:
                if self.next_is_rc(Tokens.END):
                    self.success()
                    return block
        return self.failure()

    def parse_while_stat(self) -> While or bool:
        self.save()
        if self.next_is_rc(Tokens.WHILE):
            self._expected = []
            expr = self.parse_expr()
            if expr:
                self._expected = []
                body = self.parse_do_block()
                if body:
                    self.success()
                    return While(expr, body)
            self.abort()

        return self.failure()

    def parse_repeat_stat(self) -> Repeat or bool:
        self.save()
        if self.next_is_rc(Tokens.REPEAT, False):
            self.handle_hidden_right()
            body = self.parse_block()
            if body:
                if self.next_is_rc(Tokens.UNTIL):
                    expr = self.parse_expr()
                    if expr:
                        self.success()
                        return Repeat(body, expr)

        return self.failure()

    def parse_local(self) -> Node or bool:
        self.save()
        self._expected = []
        start_token = self.next_is_rc(Tokens.LOCAL)
        if start_token:
            targets = self.parse_name_list()
            if targets:
                values = []
                self.save()
                if self.next_is_rc(Tokens.ASSIGN):
                    values = self.parse_expr_list()
                    if values:
                        self.success()
                    else:
                        self.failure()
                        self.failure()
                        self.abort()
                else:
                    self.failure()

                self.success()
                return LocalAssign(targets, values)

            self.save()

            if self.next_is_rc(Tokens.FUNCTION) and self.next_is_rc(Tokens.NAME):
                name = Name(self.text)
                body = self.parse_func_body()
                if body:
                    self.success()
                    self.success()
                    node = LocalFunction(name, body[0], body[1])
                    self.handle_hidden_right()
                    node.start_char = start_token.start
                    node.stop_char = body[1].stop_char
                    return node
            self.failure()
            self.abort()

        return self.failure()

    def parse_goto_stat(self) -> Goto or bool:
        self.save()
        if self.next_is_rc(Tokens.GOTO) and self.next_is_rc(Tokens.NAME):
            self.success()
            return Goto(Name(self.text))
        return self.failure()

    def parse_if_stat(self) -> If or bool:
        self.save()
        if self.next_is_rc(Tokens.IFTOK):
            self._expected = []
            test = self.parse_expr()
            if test:
                if self.next_is_rc(Tokens.THEN, False):
                    self.handle_hidden_right()
                    body = self.parse_block()
                    if body:
                        main = If(test, body, None)
                        root = main
                        while True:  # zero or more
                            orelse = self.parse_elseif_stat()
                            if not orelse:
                                break
                            else:
                                root.orelse = orelse
                                root = orelse

                        else_exp = self.parse_else_stat()  # optional
                        if else_exp:
                            root.orelse = else_exp
                        if self.next_is_rc(Tokens.END):
                            self.success()
                            return main
            self.abort()
        return self.failure()

    def parse_elseif_stat(self) -> ElseIf or bool:
        self.save()
        if self.next_is_rc(Tokens.ELSEIF):
            test = self.parse_expr()
            if test:
                if self.next_is_rc(Tokens.THEN, False):
                    self.handle_hidden_right()
                    body = self.parse_block()
                    if body:
                        self.success()
                        return ElseIf(test, body, None)  # orelse will be set in parent
        return self.failure()

    def parse_else_stat(self) -> Block or bool:
        self.save()
        if self.next_is(Tokens.ELSETOK):
            if self.next_is_rc(Tokens.ELSETOK, False):
                self.handle_hidden_right()
                body = self.parse_block()
                if body:
                    self.success()
                    return body
        return self.failure()

    def parse_for_stat(self) -> Fornum or Forin or bool:
        self.save()
        if self.next_is_rc(Tokens.FOR):
            self.save()
            if self.next_is_rc(Tokens.NAME):
                target = Name(self.text)
                if self.next_is_rc(Tokens.ASSIGN):
                    start = self.parse_expr()
                    if start and self.next_is_rc(Tokens.COMMA):
                        stop = self.parse_expr()
                        if stop:
                            step = 1
                            # optional step
                            if self.next_is(Tokens.COMMA) and self.next_is_rc(Tokens.COMMA):
                                step = self.parse_expr()

                            body = self.parse_do_block()
                            if not body:
                                self.failure()
                                return self.failure()
                            self.success()
                            self.success()
                            return Fornum(target, start, stop, step, body)

            self.failure_save()
            target = self.parse_name_list()
            if target and self.next_is_rc(Tokens.IN):
                iter_expr = self.parse_expr_list()
                if iter_expr:
                    body = self.parse_do_block()
                    if body:
                        self.success()
                        self.success()
                        return Forin(body, iter_expr, target)
            self.failure()

        return self.failure()

    def parse_function(self) -> Method or Function or bool:
        self.save()
        self._expected = []
        start_token = self.next_is_rc(Tokens.FUNCTION)
        if start_token:
            names = self.parse_names()
            if names:
                self.save()
                if self.next_is_rc(Tokens.COL) and self.next_is_rc(Tokens.NAME):
                    name = Name(self.text)
                    func_body = self.parse_func_body()
                    if func_body:
                        self.success()
                        self.success()
                        node = Method(names, name, func_body[0], func_body[1])
                        self.handle_hidden_right()
                        node.start_char = start_token.start
                        node.stop_char = func_body[1].stop_char
                        return node

                self.failure()

                func_body = self.parse_func_body()
                if func_body:
                    self.success()
                    node = Function(names, func_body[0], func_body[1])
                    self.handle_hidden_right()
                    node.start_char = start_token.start
                    node.stop_char = func_body[1].stop_char
                    return node
            self.abort()

        return self.failure()

    def parse_kernel(self) -> Method or Function or bool:
        self.save()
        self._expected = []
        start_token = self.next_is_rc(Tokens.KERNEL)
        if start_token:
            names = self.parse_names()
            if names:
                self.save()
                if self.next_is_rc(Tokens.COL) and self.next_is_rc(Tokens.NAME):
                    name = Name(self.text)
                    func_body = self.parse_func_body()
                    if func_body:
                        self.success()
                        self.success()
                        node = Method(names, name, func_body[0], func_body[1])
                        self.handle_hidden_right()
                        node.start_char = start_token.start
                        node.stop_char = func_body[1].stop_char
                        return node

                self.failure()

                func_body = self.parse_func_body()
                if func_body:
                    self.success()
                    node = Kernel(names, func_body[0], func_body[1])
                    self._kernels.kernels[names.id] = node
                    self.handle_hidden_right()
                    node.start_char = start_token.start
                    node.stop_char = func_body[1].stop_char
                    return node
            self.abort()

        return self.failure()

    def parse_symmetric_pairwise_kernel(self) -> Method or Function or bool:
        self.save()
        self._expected = []
        start_token = self.next_is_rc(Tokens.SYM_PAIRWISE_KERNEL)
        if start_token:
            names = self.parse_names()
            if names:
                self.save()
                if self.next_is_rc(Tokens.COL) and self.next_is_rc(Tokens.NAME):
                    name = Name(self.text)
                    func_body = self.parse_func_body()
                    if func_body:
                        self.success()
                        self.success()
                        node = Method(names, name, func_body[0], func_body[1])
                        self.handle_hidden_right()
                        node.start_char = start_token.start
                        node.stop_char = func_body[1].stop_char
                        return node

                self.failure()

                func_body = self.parse_func_body()
                if func_body:
                    self.success()
                    node = Symmetric_Pairwise_Kernel(names, func_body[0], func_body[1])
                    self._kernels.symmetric_kernels[names.id] = node
                    self.handle_hidden_right()
                    node.start_char = start_token.start
                    node.stop_char = func_body[1].stop_char
                    return node
            self.abort()

        return self.failure()

    def parse_asymmetric_pairwise_kernel(self) -> Method or Function or bool:
        self.save()
        self._expected = []
        start_token = self.next_is_rc(Tokens.ASYM_PAIRWISE_KERNEL)
        if start_token:
            names = self.parse_names()
            if names:
                self.save()
                if self.next_is_rc(Tokens.COL) and self.next_is_rc(Tokens.NAME):
                    name = Name(self.text)
                    func_body = self.parse_func_body()
                    if func_body:
                        self.success()
                        self.success()
                        node = Method(names, name, func_body[0], func_body[1])
                        self.handle_hidden_right()
                        node.start_char = start_token.start
                        node.stop_char = func_body[1].stop_char
                        return node

                self.failure()

                func_body = self.parse_func_body()
                if func_body:
                    self.success()
                    node = Asymmetric_Pairwise_Kernel(names, func_body[0], func_body[1])
                    self._kernels.asymmetric_kernels[names.id] = node
                    self.handle_hidden_right()
                    node.start_char = start_token.start
                    node.stop_char = func_body[1].stop_char
                    return node
            self.abort()

        return self.failure()
    
    def parse_dsl_main(self) -> DSL_main or bool:
        self.save()
        self._expected = []
        start_token = self.next_is_rc(Tokens.DSL_MAIN)
        if start_token:
            self.save()
            func_body = self.parse_func_body()
            if func_body:
                self.success()
                self.success()
                if self._dsl_main:
                    print("Only one main entry function expected")
                    raise MultipleMainDeclarationException
                node = DSL_main(func_body[1])
                self._dsl_main = node
                self.handle_hidden_right()
                node.start_char = start_token.start
                node.stop_char = func_body[1].stop_char
                return node
                    
                

            self.abort()
        return self.failure()

    def parse_dsl_invoke(self) -> DSL_invoke or bool:
        self.save()
        self._expected = []
        start_token = self.next_is_rc(Tokens.DSL_INVOKE)
        if start_token:
            if self.next_is_rc(Tokens.OPAR):
                args = self.parse_param_list()
                if args and self.next_is_rc(Tokens.CPAR):
                    self.success()
                    node = DSL_invoke(args, self._kernels)
                    return node
                    

            self.abort()


        return self.failure()

    def parse_particle_type(self) -> Particle_Type or bool:
        self.save()
        self._expected = []
        start_token = self.next_is_rc(Tokens.PART_TYPE)
        if start_token:
            if self.next_is_rc(Tokens.OBRACE):
                self.success()
                self.save()
                fspaces = self.parse_fspaces()
                if self.next_is_rc(Tokens.CBRACE):
                    self.success()
                    part_type = Particle_Type(fspaces)
                    if self._part_type:
                        print("Only one Particle Type declaration expected")
                        raise MultipleParticleDeclarationException
                    else:
                        self._part_type = part_type
                    return part_type
                else:
                    self.abort()
            else:
                self.abort()


            
        return self.failure()

    def parse_fspaces(self) -> List[Fspace]:
        fspaces = []
        while True:
            self.save()
            next_fspace = self.parse_fspace()
            if next_fspace:
                self.success()
                fspaces.append(next_fspace)
                self.save()
                if self.next_is_rc(Tokens.COMMA):
                    self.success()
                else:
                    self.failure()
                    return fspaces
            else:
                self.failure()
                return fspaces


    def parse_fspace(self) -> Fspace or bool:
        self.save()
        if self.next_is_rc(Tokens.NAME):
            name = self.text
            if self.next_is_rc(Tokens.COL):
                regent_type = self.parse_type(Tokens.INT) or \
                        self.parse_type(Tokens.INT32) or \
                        self.parse_type(Tokens.INT64) or \
                        self.parse_type(Tokens.UINT32) or \
                        self.parse_type(Tokens.UINT64) or \
                        self.parse_type(Tokens.FLOAT) or \
                        self.parse_type(Tokens.DOUBLE) or \
                        self.parse_type(Tokens.INT1D) or \
                        self.parse_type(Tokens.INT2D) or \
                        self.parse_type(Tokens.INT3D) or \
                        self.parse_type(Tokens.BOOL)
                if regent_type:
                    self.success()
                    fspace = Fspace(name, regent_type)
                    return fspace
                else:
                    self.abort()
            else:
                self.abort()

        return self.failure()

    def parse_type(self,  tok) -> RegentType or bool:
        self.save()
        if self.next_is_rc(tok):
            name = self.text
            node = RegentType(name)
            self.success()
            return node
        return self.failure()

    def parse_names(self) -> Name or Index or bool:
        self.save()
        if self.next_is_rc(Tokens.NAME):
            root = Name(self.text)
            while True:
                self.save()
                if self.next_is_rc(Tokens.DOT) and self.next_is_rc(Tokens.NAME):
                    self.success()
                    child = Index(String(self.text), root)
                    root = child
                else:
                    self.failure()
                    break
            self.success()
            return root
        self.failure()

    def parse_func_body(self):
        """If success, return a tuple (args, body)"""
        self.save()
        self._expected = []
        if self.next_is_rc(Tokens.OPAR, False):  # do not render right hidden
            self.handle_hidden_right()  # render hidden after new level
            args = self.parse_param_list()
            if args is not None:  # may be an empty table
                if self.next_is_rc(Tokens.CPAR, False):  # do not render right hidden
                    self.handle_hidden_right()  # render hidden after new level
                    body = self.parse_block()
                    if body:
                        self._expected = []
                        token = self.next_is_rc(Tokens.END, False)
                        if token:
                            body.stop_char = token.stop
                            self.success()
                            return args, body
                        else:
                            self.abort()
                else:
                    self.abort()
        return self.failure()

    def parse_param_list(self) -> List[Expression] or bool:
        param_list: List[Expression] = self.parse_name_list()
        if param_list:
            self.save()
            if self.next_is_rc(Tokens.COMMA) and \
                    self.next_is_rc(Tokens.VARARGS):
                self.success()
                param_list.append(Varargs())
                return param_list
            else:
                self.failure()
                return param_list

        self.save()
        if self.next_is_rc(Tokens.VARARGS):
            self.success()
            return [Varargs()]

        self.success()
        return []

    def parse_name_list(self) -> List[Name] or bool:
        self.save()
        names: List[Name] = []
        if self.next_is_rc(Tokens.NAME):
            names.append(Name(self.text))
            while True:
                self.save()
                if self.next_is_rc(Tokens.COMMA) and self.next_is_rc(Tokens.NAME):
                    names.append(Name(self.text))
                    self.success()
                else:
                    self.failure()
                    break
            self.success()
            return names
        return self.failure()

    def parse_label(self) -> Label or bool:
        self.save()
        if self.next_is_rc(Tokens.COLCOL) and self.next_is_rc(Tokens.NAME):
            name = Name(self.text)
            if self.next_is_rc(Tokens.COLCOL):
                self.success()
                return Label(name)

        return self.failure()

    def parse_callee(self) -> Expression or bool:
        self.save()
        if self.next_is_rc(Tokens.OPAR):
            expr = self.parse_expr()
            if expr:
                if self.next_is_rc(Tokens.CPAR):
                    self.success()
                    # TODO: create a node to indicate parenthesis
                    return expr
        self.failure()
        self.save()
        if self.next_is_rc(Tokens.NAME):
            self.success()
            return Name(self.text)
        return self.failure()

    def parse_expr(self) -> Expression or bool:
        return self.parse_or_expr()

    def parse_or_expr(self) -> Expression or bool:
        self.save()
        left = self.parse_and_expr()
        if left:
            while True:
                self.save()
                if self.next_is_rc(Tokens.OR):
                    right = self.parse_and_expr()
                    if right:
                        self.success()
                        left = OrLoOp(left, right)
                    else:
                        self.failure()
                        return self.failure()
                else:
                    self.failure()
                    break
            self.success()
            return left

        return self.failure()

    def parse_and_expr(self) -> Expression or bool:
        self.save()
        left = self.parse_rel_expr()
        if left:
            while True:
                self.save()
                if self.next_is_rc(Tokens.AND):
                    right = self.parse_rel_expr()
                    if right:
                        self.success()
                        left = AndLoOp(left, right)
                    else:
                        self.failure()
                        return self.failure()
                else:
                    self.failure()
                    break
            self.success()
            return left

        return self.failure()

    def parse_rel_expr(self) -> Expression or bool:
        self.save()
        left = self.parse_concat_expr()
        if left:
            self.save()
            if self.next_in_rc(self.REL_OPERATORS):
                op = self.type
                right = self.parse_concat_expr()
                if right:
                    self.success()
                    if op == Tokens.LT:
                        left = LessThanOp(left, right)
                    elif op == Tokens.GT:
                        left = GreaterThanOp(left, right)
                    elif op == Tokens.LTEQ:
                        left = LessOrEqThanOp(left, right)
                    elif op == Tokens.GTEQ:
                        left = GreaterOrEqThanOp(left, right)
                    elif op == Tokens.NEQ:
                        left = NotEqToOp(left, right)
                    elif op == Tokens.EQ:
                        left = EqToOp(left, right)
                else:
                    self.failure()
                    return self.failure()
            else:
                self.failure()
            self.success()
            return left
        return self.failure()

    def parse_concat_expr(self) -> Expression or bool:
        self.save()
        left = self.parse_add_expr()
        if left:
            while True:
                self.save()
                if self.next_is_rc(Tokens.CONCAT):
                    self._expected = []
                    right = self.parse_add_expr()
                    if right:
                        self.success()
                        left = Concat(left, right)
                    else:
                        self.failure()
                        self.failure()
                        self.abort()
                else:
                    self.failure()
                    break
            self.success()
            return left

        return self.failure()

    def parse_add_expr(self) -> Expression or bool:
        self.save()
        left = self.parse_mult_expr()
        if left:
            while True:
                self.save()
                if self.next_in_rc([Tokens.ADD, Tokens.MINUS]):
                    op = self.type
                    right = self.parse_mult_expr()
                    if right:
                        self.success()
                        if op == Tokens.ADD:
                            left = AddOp(left, right)
                        elif op == Tokens.MINUS:
                            left = SubOp(left, right)
                    else:
                        self.failure()
                        return self.failure()
                else:
                    self.failure()
                    break
            self.success()
            return left

        return self.failure()

    def parse_mult_expr(self) -> Expression or bool:
        self.save()
        left = self.parse_bitwise_expr()
        if left:
            while True:
                self.save()
                if self.next_in_rc([Tokens.MULT,
                                    Tokens.DIV,
                                    Tokens.MOD,
                                    Tokens.FLOOR]):
                    op = self.type
                    right = self.parse_bitwise_expr()
                    if right:
                        self.success()
                        if op == Tokens.MULT:
                            left = MultOp(left, right)
                        elif op == Tokens.DIV:
                            left = FloatDivOp(left, right)
                        elif op == Tokens.MOD:
                            left = ModOp(left, right)
                        elif op == Tokens.FLOOR:
                            left = FloorDivOp(left, right)
                    else:
                        self.failure()
                        return self.failure()
                else:
                    self.failure()
                    break
            self.success()
            return left

        return self.failure()

    def parse_bitwise_expr(self) -> Expression or bool:
        self.save()
        left = self.parse_unary_expr()
        if left:
            while True:
                self.save()
                if self.next_in_rc([Tokens.BITAND,
                                    Tokens.BITOR,
                                    Tokens.BITNOT,
                                    Tokens.BITRSHIFT,
                                    Tokens.BITRLEFT]):
                    op = self.type
                    right = self.parse_unary_expr()
                    if right:
                        self.success()
                        if op == Tokens.BITAND:
                            left = BAndOp(left, right)
                        elif op == Tokens.BITOR:
                            left = BOrOp(left, right)
                        elif op == Tokens.BITNOT:
                            left = BXorOp(left, right)
                        elif op == Tokens.BITRSHIFT:
                            left = BShiftROp(left, right)
                        elif op == Tokens.BITRLEFT:
                            left = BShiftLOp(left, right)
                    else:
                        self.failure()
                        return self.failure()
                else:
                    self.failure()
                    break
            self.success()
            return left

        return self.failure()

    def parse_unary_expr(self) -> Expression or bool:
        self.save()
        if self.next_is_rc(Tokens.MINUS):
            expr = self.parse_unary_expr()
            if expr:
                self.success()
                return UMinusOp(expr)

        self.failure_save()
        if self.next_is_rc(Tokens.LENGTH):
            expr = self.parse_pow_expr()
            if expr:
                self.success()
                return ULengthOP(expr)

        self.failure_save()
        if self.next_is_rc(Tokens.NOT):
            expr = self.parse_unary_expr()
            if expr:
                self.success()
                return ULNotOp(expr)

        self.failure_save()
        if self.next_is_rc(Tokens.BITNOT):
            expr = self.parse_unary_expr()
            if expr:
                self.success()
                return UBNotOp(expr)

        self.failure_save()
        expr = self.parse_pow_expr()
        if expr:
            self.success()
            return expr

        return self.failure()

    def parse_pow_expr(self) -> Expression or bool:
        self.save()
        left = self.parse_atom()
        if left:
            while True:
                self.save()
                if self.next_is_rc(Tokens.POW):
                    right = self.parse_atom()
                    if right:
                        self.success()
                        left = ExpoOp(left, right)
                    else:
                        self.failure()
                        return self.failure()
                else:
                    self.failure()
                    break
            self.success()
            return left

        self.failure()

    def parse_atom(self) -> Expression or bool:
        atom = self.parse_var()
        if atom:
            return atom
        atom = self.parse_function_literal()
        if atom:
            return atom
        atom = self.parse_table_constructor()
        if atom:
            return atom
        if self.next_is(Tokens.VARARGS) and self.next_is_rc(Tokens.VARARGS):
            return Varargs()

        if self.next_is(Tokens.NUMBER) and self.next_is_rc(Tokens.NUMBER):
            # TODO: optimize
            # using python number eval to parse lua number
            try:
                number = ast.literal_eval(self.text)
            except:
                # exception occurs with leading zero number: 002
                number = float(self.text)
            return Number(number)

        if self.next_is(Tokens.STRING) and self.next_is_rc(Tokens.STRING):
            return self.parse_lua_str(self.text)

        if self.next_is(Tokens.NIL) and self.next_is_rc(Tokens.NIL):
            return Nil()

        if self.next_is(Tokens.TRUE) and self.next_is_rc(Tokens.TRUE):
            return TrueExpr()

        if self.next_is(Tokens.FALSE) and self.next_is_rc(Tokens.FALSE):
            return FalseExpr()
        return None

    @staticmethod
    def parse_lua_str(lua_str) -> String:
        p = re.compile(r'^\[=+\[(.*)\]=+\]')  # nested quote pattern
        return String(lua_str)

    def parse_function_literal(self) -> AnonymousFunction or bool:
        self.save()
        if self.next_is_rc(Tokens.FUNCTION):
            func_body = self.parse_func_body()
            if func_body:
                self.success()
                node = AnonymousFunction(func_body[0], func_body[1])
                self.handle_hidden_right()
                return node

        return self.failure()

    def parse_table_constructor(self, render_last_hidden=True) -> Table or bool:
        self.save()
        if self.next_is_rc(Tokens.OBRACE, False):  # do not render right hidden
            self.handle_hidden_right()  # render hidden after new level

            fields = self.parse_field_list()
            if self.next_is_rc(Tokens.CBRACE, render_last_hidden):
                self.success()

                array_like_index = 1
                if fields:  # optional
                    for field in fields:
                        if field.key is None:
                            field.key = Number(array_like_index)
                            array_like_index += 1

                return Table(fields or [])

        return self.failure()

    def parse_field_list(self) -> List[Field] or bool:
        field_list = []
        self.save()
        field = self.parse_field()
        if field:
            field_list.append(field)
            while True:
                self.save()
                if self.next_in_rc([Tokens.COMMA, Tokens.SEMCOL]):
                    inline_com = self.get_inline_comment()
                    if inline_com:
                        field.comments.append(inline_com)
                    field = self.parse_field()
                    if field:
                        field_list.append(field)
                        self.success()
                    else:
                        self.success()
                        self.success()
                        return field_list
                else:

                    field.comments.extend(self.get_comments())
                    self.failure()
                    break
            self.parse_field_sep()
            self.success()
            return field_list
        return self.failure()

    def parse_field(self) -> Field or bool:
        self.save()

        if self.next_is_rc(Tokens.OBRACK):
            key = self.parse_expr()
            if key and self.next_is_rc(Tokens.CBRACK):
                if self.next_is_rc(Tokens.ASSIGN):
                    comments = self.get_comments()
                    value = self.parse_expr()
                    if value:
                        self.success()
                        return Field(key, value, comments, between_brackets=True)

        self.failure_save()
        if self.next_is_rc(Tokens.NAME):
            key = Name(self.text)
            if self.next_is_rc(Tokens.ASSIGN):
                comments = self.get_comments()
                value = self.parse_expr()
                if value:
                    self.success()
                    return Field(key, value, comments)

        self.failure_save()
        comments = self.get_comments()
        value = self.parse_expr()
        if value:
            self.success()
            # noinspection PyTypeChecker
            return Field(None, value, comments)  # Key will be set in parse_table_constructor

        return self.failure()

    def parse_field_sep(self) -> bool:
        self.save()
        if self.next_in_rc([Tokens.COMMA, Tokens.SEMCOL]):
            return self.success()
        return self.failure()
