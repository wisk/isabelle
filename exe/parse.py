#!/usr/bin/python2

# ref: https://stackoverflow.com/questions/23879784/parse-mathematical-expressions-with-pyparsing
# ref: http://qiita.com/knoguchi/items/6f9b7383b7252a9ebdad

from pyparsing import *
from pprint import pprint

# operator
_open_paren    = Literal('(').suppress()
_close_paren   = Literal(')').suppress()
_open_bracket  = Literal('{').suppress()
_close_bracket = Literal('}').suppress()
_open_square   = Literal('[').suppress()
_close_square  = Literal(']').suppress()
_open_angle    = Literal('<').suppress()
_close_angle   = Literal('>').suppress()
_quote         = Literal("'").suppress()
_double_quote  = Literal('"').suppress()
_comma         = Literal(',').suppress()
_colon         = Literal(':').suppress()
_semicolon     = Literal(';').suppress()
_assign        = Literal('=').suppress()
_dot           = Literal('.').suppress()

# comparison
_equal             = Keyword('==').setResultsName('cmp_equal')
_different         = Keyword('!=').setResultsName('cmp_different')
_superior_or_equal = Keyword('>=').setResultsName('cmp_superior_or_equal')
_inferior_or_equal = Keyword('<=').setResultsName('cmp_inferior_or_equal')
_superior          = Keyword('>').setResultsName('cmp_superior')
_inferior          = Keyword('<').setResultsName('cmp_inferior')
_comparison_operators = _equal | _different | _superior_or_equal | _inferior_or_equal | _superior | _inferior

# unary operator
_not    = Literal('~').setResultsName('not')
_negate = Literal('-').setResultsName('negate')
_unary_operator = Group(_not | _negate).setResultsName('op_un')


# binary operator
_add    = Literal('+').setResultsName('add')
_sub    = Literal('-').setResultsName('sub')
_mul    = Literal('*').setResultsName('mul')
_div    = Literal('/').setResultsName('div')
_mod    = Literal('%').setResultsName('mod')

_and    = Literal('&').setResultsName('and')
_or     = Literal('|').setResultsName('or')
_xor    = Literal('^').setResultsName('xor')

_lsl    = Literal('<<').setResultsName('lsl')
_lsr    = Literal('>>').setResultsName('lsr')

_binary_operators = (_add | _sub | _mul | _div | _mod | _and | _or | _xor | _lsl | _lsr)

# label
_label       = Word(alphas + '_', bodyChars=alphanums + '_')
_label       = Group(_label + ZeroOrMore(_dot + _label)).setResultsName('label').setName('label')

# literal
_binary_literal      = Combine(Literal('0b') + Word('01')).setResultsName('lit_bin')
_decimal_literal     = Word( nums ).setResultsName('lit_dec')
_hexadecimal_literal = Combine(Literal('0x') + Word('0123456789ABCDEFabcdef')).setResultsName('lit_hex')
_string_literal      = quotedString.setResultsName('lit_str')
_float_literal       = Combine(Word( nums ).setResultsName('decimal') + _dot + Word( nums ).setResultsName('fractional')).setResultsName('lit_flt')
_literal             = (_float_literal | _binary_literal | _hexadecimal_literal | _decimal_literal | _string_literal).setName('literal')

_value = Forward()
_statment = Forward()
_predicat = Forward()

UNARY,BINARY=1,2
_expression = (infixNotation(\
        _value,\
        [\
            (_not | _negate, UNARY, opAssoc.RIGHT),\
            (_mul | _div | _mod, BINARY, opAssoc.LEFT),\
            (_add | _sub, BINARY, opAssoc.LEFT),\
            (_lsl | _lsr | _and | _or | _xor, BINARY, opAssoc.LEFT),\
        ])).setResultsName('expr').setName('expr').setDebug()

_assignment_statement = Group(Group(_label).setResultsName('dst') + _assign + Group(_expression).setResultsName('src') + _semicolon).setResultsName('assign').setName('name')

_statments = (_open_bracket + OneOrMore(_statment) + _close_bracket).setName('statments')

# function
_function_name = Group(_label).setResultsName('func_name')
_function_parameters = Group(_open_paren + delimitedList(Group(_expression)) + _close_paren).setResultsName('func_param')
_function_statment = Group((_function_name) + (_function_parameters)).setResultsName('func').setName('func')

# if / else
_else_statment =\
    Keyword('else') +\
    Group(_statment | _statments).setResultsName('else_body').setName('else_body')

_then_statment = Group(\
    (_statment | _statments)\
).setResultsName('then_body').setName('then_body')

_if_statment = Group(\
    Keyword('if') + Group(_predicat).setResultsName('if_predicat') +\
        _then_statment +\
    Optional(_else_statment)\
).setResultsName('cond_if').setName('cond_if')

# case / when
_when_statment = Group(\
    Keyword('when').suppress() + _open_paren + Group(_literal).setResultsName('when_value') + _close_paren +\
        Group(_statment | _statments).setResultsName('when_body')\
).setResultsName('cond_when')

_case_statment = Group(\
    Keyword('case') + Group(_predicat).setResultsName('case_predicat') +\
        _open_bracket +\
            (ZeroOrMore(_when_statment)).setResultsName('case_when') +\
        _close_bracket\
).setResultsName('cond_case').setName('cond_case')

#_paren_value = _open_paren + _value + _close_paren
#_value << Group(Optional(_unary_operator).setResultsName('op_un') + (_function_statment | _label | _literal)) + Optional(_binary_operators + (_value | _paren_value)).setResultsName('op_bin')
#_value << (_function_statment | _label | _literal)
_value << Group(Optional(_unary_operator) + Group(_function_statment | _label | _literal))
_statment << Group(Group(_function_statment) + _semicolon).setResultsName('statment').setName('statment')
_predicat << (_open_paren + _value + _close_paren).setResultsName('predicat')

_all = OneOrMore(_if_statment | _case_statment | _statment | _statments | _assignment_statement)

import json
class PyParseEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ParseResults):
            x = obj.asDict()
            if x.keys():
                obj = x
            else:
                x = obj.asList()
                if len(x) == 1:
                    obj = x[0]
                else:
                    obj = x
        else:
            obj = super(PyParseEncoder, self).default(obj)
        return obj

def format_parsed_code(s):
    if not s:
        raise Exception('invalid code')
    return json.dumps(s, cls=PyParseEncoder, sort_keys=False, indent=2)

def parse(s):
    try:
        res = _all.parseString(s, parseAll=True)
        return res
    except Exception as e:
        if hasattr(e, 'line'):
            print e.line
            print ' ' * (e.column - 1) + '^'
        print e

class AST:
    def __init__(self):
        pass

    def __del__(self):
        pass

    def visit(self, node):
        if type(node) == str:
            raise Exception('bad type of node')
        print node.dump()
        if not node.haskeys():
            node = node[0]
            if not node.haskeys():
                raise Exception('no key in node')
        node_keys = node.keys()
        if len(node_keys) != 1:
            raise Exception('more than one key in node: %s' % node_keys)

        node_name = node_keys[0]
        print node_name

        if node_name == 'statment':
            return self.visit_statment(node[0])

        if node_name == 'predicat':
            return self.visit_predicat(node[0])

        if node_name == 'label':
            return self.visit_label(node[0])

        if node_name == 'expr':
            return self.visit_expression(node)

        if node_name == 'op_un':
            return self.visit_unary_operator(node)

        if node_name == 'lit_bin':
            return self.visit_literal_binary(node[0])
        if node_name == 'lit_hex':
            return self.visit_literal_hexadecimal(node[0])
        if node_name == 'lit_dec':
            return self.visit_literal_decimal(node[0])
        if node_name == 'lit_str':
            return self.visit_literal_string(node[0])

        if node_name == 'assign':
            return self.visit_assignment(node[0])
        if node_name == 'func':
            return self.visit_function(node[0])
        if node_name == 'cond_if':
            return self.visit_if(node[0])
        if node_name == 'cond_case':
            return self.visit_case(node[0])

        raise Exception('unhandled node type: %s' % node_name)

    def visit_statment(self, node):
        return self.visit(node[0]) + ';'

    def visit_predicat(self, node):
        return self.visit(node)

    def visit_label(self, node):
        assert(len(node) != 0)

        if node[0] == 'field':
            return node[0]

        if node[0] == 'insn':
            res = 'rInsn.';
            if node[1] == 'mnem':
                res += 'Mnemonic().'

                if node[2] == 'add_suffix':
                    res += 'AddSuffix'

                    return res

            if node[1] == 'add_oprd':
                res += 'AddOperand'

                return res


        if node[0] == 'id':
            return 'expr::MakeId'

        if node[0] == 'mem':
            return 'expr::MakeMem'

        if node[0] == 'int':
            return 'Exp::MakeBv'

        if node[0] == 'arm':
            return node[1]

        raise Exception('unknown label: %s' % node)

    def visit_expression(self, node):
        aa

    def visit_unary_operator(self, node):
        val = self.visit(node[1])
        return node[0][0] + val

    def visit_literal_string(self, node):
        return node

    def visit_literal_hexadecimal(self, node):
        return node

    def visit_literal_binary(self, node):
        return '0x%08x' % int(node[2:], 2)

    def visit_literal_decimal(self, node):
        return node

    def visit_assignment(self, node):
        dst = self.visit(node.dst)
        src = self.visit(node.src)

        return '%s = %s;' % (dst, src)

    def visit_function(self, node):
        func_name = self.visit(node.func_name)
        func_param = [ self.visit(x) for x in node.func_param ]

        return '%s(%s)' % (func_name, ', '.join(func_param))

    def visit_if(self, node):
        if_predicat = self.visit(node.if_predicat)
        then_body = self.visit(node.then_body)

        if not hasattr(node, 'else_body'):
            return '''\
if (%s)
{
  %s
}''' % (if_predicat, then_body)

        else_body = self.visit(node.else_body)
        return '''\
if (%s)
{
  %s
}
else
{
  %s
}''' % (if_predicat, then_body, else_body)

    def visit_case(self, node):
        case_predicat = self.visit(node.case_predicat)
        case_when = [ (self.visit(x.when_value[0]), self.visit(x.when_body)) for x in node.case_when ]

        cases_body = ''
        for case_value, case_body in case_when:
            print 'v:', case_value
            print 'b:', case_body
            cases_body += '''\
case (%s):
{
  %s
  break;
}
''' % (case_value, case_body)

        return '''\
switch (%s)
{
%s}
''' % (case_predicat, cases_body)

def compile_to_cpp(ast):
    return 'return false;'

test0 = '''\
a = 0x1000;
'''

test1 = '''\
insn.add_oprd(int(32, 0x0));
'''

test1='int((0x10 + field("U")) * (2 >> 4), "aa");'

test2 = '''\
if (field("U"))
  insn.add_oprd(id(arm.Register("GPR32", field("Rm"))));
else
  insn.add_oprd(-id(arm.Register("GPR32", field("Rm"))));
'''

test3 = '''\
insn.add_oprd(mem(16,
  id(arm.Register("GPR32", field("<Rn>"))) + int(32, field("imm"))));
'''

test4 = '''\
insn.add_oprd(id("pc") + (field("imm") << 2));
'''

test5 = '''\
insn.add_oprd(flt(0.0));
'''

test6 = '''\
insn.add_oprd(mem(32,
  id(arm.Register("GPR32", field("<Rn>"))) + id(arm.Register("GPR32", field("<Rm>")))));
'''

test7 = '''\
var(32, "off");
off = int(32, field('imm8') << 2);
'''

test8 = '''\
case (field("size"))
{
  when (0b00)
    insn.mnem.add_suffix("8");
  when (0b01)
    insn.mnem.add_suffix("16");
  when (0b10)
    insn.mnem.add_suffix("32");
}
'''

def print_ast(s):
    print '#' * 80
    print s
    print '#' * 80
    ast = AST()
    res = ast.visit(parse(s))
    print '_'*80
    print res
    print '_'*80

if __name__ == '__main__':
##    print format_parsed_code(parse(test0))
##    print format_parsed_code(parse(test1))
##    print format_parsed_code(parse(test2))
##    print format_parsed_code(parse(test3))
##    print format_parsed_code(parse(test4))
##    print format_parsed_code(parse(test5))
##    print format_parsed_code(parse(test6))
##    print format_parsed_code(parse(test7))
##    print format_parsed_code(parse(test8))

    #print_ast(test0)
    print_ast(test1)
    print_ast(test2)
    print_ast(test3)
    print_ast(test4)
    print_ast(test5)
    print_ast(test6)
    print_ast(test7)
    print_ast(test8)

