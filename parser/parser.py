#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
from arpeggio.peg import ParserPEG, PTNodeVisitor, visit_parse_tree


test0 = '''\
a = 1.000;
'''

test1 = '''\
insn.add_oprd(int(32, 0x0));
'''

test1='int((0x10 + field("U")) * (2 >> 4), 3);'

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
off = int(32, field("imm8") << 2);
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

def test_parser(parser, test):
    # print '_' * 80
    # print test
    # print '_' * 80
    parse_tree = parser.parse(test)
    print parse_tree
    vst = IsabelleVisitor(debug=False)
    result = visit_parse_tree(parse_tree, vst)
    print '*' * 80
    print result
    print '*' * 80
    print vst.res
    print '_' * 80

class IsabelleVisitor(PTNodeVisitor):
    def __init__(self, *args, **kwargs):
        super(IsabelleVisitor, self).__init__(*args, **kwargs)
        self.res = ''
        self.var = []

    def visit_label(self, node, children):
        label = children[0]

        if label in self.var:
            return label

        if label == 'int':
            res = 'expr::MakeBv'
            self.res += res
            return res

        if label == 'field':
            res = 'ExtractField'
            self.res += res
            return res

        if label == 'id':
            res = 'expr::MakeId'
            self.res += res
            return res

        if label == 'mem':
            res = 'expr::MakeMem'
            self.res += res
            return res

        if label == 'var':
            res = 'expr::MakeVar'
            self.res += res
            return res

        if label == 'flt':
            res = 'BitVector'
            self.res += res
            return res

        if label == 'insn':
            meth = children[1]

            if meth == 'add_oprd':
                res = 'rInsn.AddOperand'
                self.res += res
                return res

        if label == 'arm':
            res = children[1]
            self.res += res
            return res

        res = label
        self.res += res
        return res
        raise Exception('unknown label: %s' % label)

    def visit_literal_binary(self, node, children):
        res = '%08x' % int(node.value[2:], 2)
        self.res += res
        return res

    def visit_literal_decimal(self, node, children):
        res = node.value
        self.res += res
        return res

    def visit_literal_hexadecimal(self, node, children):
        res = node.value
        self.res += res
        return res

    def visit_literal_string(self, node, children):
        res = node.value
        self.res += res
        return res

    def visit_literal_float(self, node, children):
        res = node.value
        self.res += res
        return res

    def visit_function(self, node, children):
        res = '%s(%s)' % (children[0], ', '.join(children[1:]))
        self.res += res
        return res


def main(debug = False):

    isabelle_grammar = open(os.path.join(os.path.dirname(__file__), 'isabelle.peg'), 'r').read()
    parser = ParserPEG(isabelle_grammar, 'code', debug = debug)

    # test_parser(parser, test0)
    test_parser(parser, test1)
    test_parser(parser, test2)
    test_parser(parser, test3)
    test_parser(parser, test4)
    test_parser(parser, test5)
    test_parser(parser, test6)
    test_parser(parser, test7)
    test_parser(parser, test8)

if __name__ == '__main__':
    main(debug=False)
