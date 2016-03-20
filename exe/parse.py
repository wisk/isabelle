#!/usr/bin/python2

from pyparsing import *

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

_equal             = Keyword('==').setResultsName('cmp_equal')
_different         = Keyword('!=').setResultsName('cmp_different')
_superior_or_equal = Keyword('>=').setResultsName('cmp_superior_or_equal')
_inferior_or_equal = Keyword('<=').setResultsName('cmp_inferior_or_equal')
_superior          = Keyword('>').setResultsName('cmp_superior')
_inferior          = Keyword('<').setResultsName('cmp_inferior')
_comparison_operators = _equal | _different | _superior_or_equal | _inferior_or_equal | _superior | _inferior

_not    = Literal('~').setResultsName('not')
_negate = Literal('-').setResultsName('negate')
_unary_operator = (_not | _negate)

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

_label       = Word(alphas + '_', bodyChars=alphanums + '_')
_label       = Group(_label + ZeroOrMore(_dot + _label)).setResultsName('label')

_binary_literal      = '0b' + Word('01').setResultsName('bin')
_decimal_literal     = Word( nums ).setResultsName('dec')
_hexadecimal_literal = '0x' + Word('0123456789ABCDEFabcdef').setResultsName('hex')
_string_literal      = quotedString.setResultsName('str')
_float_literal       = _decimal_literal + _dot + _decimal_literal
_literal             = (_float_literal | _binary_literal | _hexadecimal_literal | _decimal_literal | _string_literal)

_value = Forward()
_statment = Forward()
_predicat = Forward()

_assignment_statement = _label + _assign + _value + _semicolon

_statments = _open_bracket + OneOrMore(_statment) + _close_bracket

_function_name = _label.setResultsName('func_name')
_function_parameters = Optional(_value + ZeroOrMore(_comma + (_value))).setResultsName('func_param')
_function_statment = Group(_function_name + _open_paren + _function_parameters + _close_paren).setResultsName('func')

_else_statment =\
    Keyword('else') +\
    (_statment | _statments)

_if_statment = Group(\
    Keyword('if') + _predicat +\
        (_statment | _statments) +\
    Optional(_else_statment)\
).setResultsName('cond_if')

_when_statment = Group(\
    Keyword('when') + _open_paren + _value + _close_paren +\
        (_statment | _statments)).setResultsName('when')
_case_statment = Group(\
    Keyword('case') + _predicat +\
        _open_bracket +\
            OneOrMore(_when_statment) +\
        _close_bracket\
).setResultsName('case')

_paren_value = _open_paren + _value + _close_paren
_value << Optional(_unary_operator) + (_function_statment | _label | _literal) + Optional(_binary_operators + (_value | _paren_value))
_statment << _function_statment + _semicolon
_predicat << (_open_paren + _value + _close_paren)

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

test0 = '''\
insn.mnem.set("vabal");
insn.add_attr("support-it-block");
insn.mnem.add_suffix(".");
if (field("U"))
  insn.mnem.add_suffix("U");
else
  insn.mnem.add_suffix("S");
case (field("size"))
{
  when (0b00)
    insn.mnem.add_suffix("8");
  when (0b01)
    insn.mnem.add_suffix("16");
  when (0b10)
    insn.mnem.add_suffix("32");
}
insn.add_oprd(id(arm.Register("SIMDR128", field("Qd"))));
insn.add_oprd(id(arm.Register("SIMDR64", field("Dn"))));
insn.add_oprd(id(arm.Register("SIMDR64", field("Dm"))));
'''

test1 = '''\
insn.add_oprd(int(32, 0x0));
'''

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
off = int(32, field('imm8') << 2);
'''

if __name__ == '__main__':
    print format_parsed_code(parse(test0))
    print format_parsed_code(parse(test1))
    print format_parsed_code(parse(test2))
    print format_parsed_code(parse(test3))
    print format_parsed_code(parse(test4))
    print format_parsed_code(parse(test5))
    print format_parsed_code(parse(test6))
    print format_parsed_code(parse(test7))
