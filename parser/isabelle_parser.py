#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
from arpeggio.peg import ParserPEG, PTNodeVisitor, visit_parse_tree

def convert_decoder_to_medusa(arch, insn):
    isabelle_grammar = open(os.path.join(os.path.dirname(__file__), 'isabelle.peg'), 'r').read()
    parser = ParserPEG(isabelle_grammar, 'code', debug = False)
    parse_tree = parser.parse(insn['decoder'])
    return visit_parse_tree(parse_tree, IsabelleVisitor(arch, insn, debug = False)) + "\n"

def convert_semantic_to_medusa(arch, insn):
    isabelle_grammar = open(os.path.join(os.path.dirname(__file__), 'isabelle.peg'), 'r').read()
    parser = ParserPEG(isabelle_grammar, 'code', debug = False)
    parse_tree = parser.parse(insn['semantic'])
    return visit_parse_tree(parse_tree, IsabelleVisitor(arch, insn, debug = False)) + "\n"

def indent(s, lvl = 1):
    res = ''
    for l in s.split('\n'):
        if len(l) == 0:
            continue
        res += '  ' * lvl + l + '\n'
    return res

class IsabelleVisitor(PTNodeVisitor):
    def __init__(self, arch, insn, *args, **kwargs):
        super(IsabelleVisitor, self).__init__(*args, **kwargs)
        self.var = {}
        self.arch = arch
        self.insn = insn

    def _get_architecture_name(self):
        return self.arch['name']

    def _get_field_bitsize(self, field_name):
        for field in self.insn['encoding']:
            cur_field_name = field
            cur_field_bitsize = 0
            if '#' in cur_field_name:
                cur_field_name, cur_field_bitsize = field.split('#')
            if cur_field_name == field_name:
                return int(cur_field_bitsize)
        raise Exception('unknown field: %s' % field_name)

    def _extract_bits(self, pattern):
        res = [] # beg, end
        enc = self.insn['encoding']
        beg = 0
        end = 0
        off = 0

        found = False
        for bitfield in enc[::-1]:
            bitfield_size = 1
            if '#' in bitfield:
                bitfield, bitfield_size = bitfield.split('#')
                bitfield_size = int(bitfield_size)

            if bitfield == pattern and not found:
                beg = off
                found = True
            elif bitfield != pattern and found:
                end = off - 1
                found = False
                res.append((beg, end))

            off += bitfield_size

        last_enc = enc[0]
        if '#' in last_enc:
            last_enc = last_enc.split('#')[0]
        if end == 0 and last_enc == pattern:
            end = off - 1
            res.append((beg, end))

        return res

    def _generate_extract_bits(self, pattern, scale = 0):
        bits = self._extract_bits(pattern)
        res = []

        zx_bit = 0
        for beg, end in bits:

            scale_str = ''
            if zx_bit != 0:
                scale_str = ' << %d' % zx_bit

            if beg == end:
                res.append('ExtractBit<%d>(Opcode)%s' % (beg, scale_str))
            else:
                res.append('ExtractBits<%d, %d>(Opcode)%s' % (beg, end, scale_str))

            zx_bit += end - beg + 1

        if len(res) == 0:
            return None

        scale_str = ''
        if scale != 0:
            scale_str = ' << %d' % scale
        return '(%s)%s' % (' | '.join(res), scale_str)

    def visit_bitfield(self, node, children):
        bitfield = children[::-1]
        res = []
        scale = 0

        for field in bitfield:
            if field[0] == '"' and field[-1] == '"':
                res.append(self._generate_extract_bits(field[1:-1], scale))
                scale += self._get_field_bitsize(field[1:-1])
            else:
                res.append('%d' % int(field))
                scale += len(field)

        return ' | '.join(res[::-1])


    def visit_label(self, node, children):
        label = children[0]

        if label in self.var:
            return 'Expr::MakeVar("%s", VariableExpression::Use)' % label

        if label == 'ite':
            return 'Expr::MakeTernary'

        if label == 'sx':
            return 'SignExtend'

        if label == 'zx':
            return 'ZeroExtend'

        if label == 'bsz':
            return '__bit_size'

        if label == 'bcast':
            return '__bit_cast'

        if label == 'cpu_info':
            return '&m_CpuInfo'

        if label == 'int':
            return 'Expr::MakeBitVector'

        if label == 'field':
            return '__field'

        if label == 'alloc_var':
            return '__alloc_var'

        if label == 'free_var':
            return '__free_var'

        if label == 'id':
            return 'Expr::MakeId'

        if label == 'vec_id':
            return 'Expr::MakeVecId'

        if label == 'mem':
            return 'Expr::MakeMem'

        if label == 'var':
            return 'Expr::MakeVar'

        if label == 'flt':
            return '__flt'

        if label == 'insn':
            meth = children[1]

            if meth.startswith('oprd'):
                oprd_no = int(meth[len('oprd'):])

                return 'rInsn.GetOperand(%d)' % oprd_no

            if meth == 'add_oprd':
                return 'rInsn.AddOperand'

            if meth == 'add_attr':
                return 'rInsn.AddAttribute'

            if meth == 'set_cond':
                return 'rInsn.SetTestedFlags'

            if meth == 'sem':
                return 'rInsn.AddPostSemantic'

            if meth == 'mnem':
                meth = children[2]

                if meth == 'set':
                    return 'rInsn.SetMnemonic'

                if meth == 'add_suffix':
                    return 'rInsn.AddMnemonicSuffix'

        if label == self._get_architecture_name():
            meth = children[1]

            if meth == 'RegisterFromName':
                return 'm_CpuInfo.ConvertNameToIdentifier'

            return '::'.join(children)

        return label
        # raise Exception('unhandled label: %s' % label)

    def visit_literal_binary(self, node, children):
        return '0x%08x' % int(node.value[2:], 2)

    def visit_literal_decimal(self, node, children):
        return node.value

    def visit_literal_hexadecimal(self, node, children):
        return node.value

    def visit_literal_string(self, node, children):
        return node.value

    def visit_literal_float(self, node, children):
        return node.value

    def visit_expr_0(self, node, children):
        return ''.join(children)
    def visit_expr_1(self, node, children):
        return ' '.join(children)
    def visit_expr_2(self, node, children):
        return ' '.join(children)
    def visit_expr_3(self, node, children):
        return ' '.join(children)
    def visit_expr_4(self, node, children):
        return ' '.join(children)
    def visit_expr_5(self, node, children):
        return ' '.join(children)
    def visit_expr_6(self, node, children):
        return ' '.join(children)
    def visit_expr_7(self, node, children):
        return ' '.join(children)

    def visit_expression(self, node, children):
        assert(len(children) != 0)
        if (len(children) == 1):
            return children[0]
        assert(len(children) == 3)
        return ' '.join(children)

    def visit_assignment(self, node, children):
        assert(len(children) == 2)
        return 'Expr::MakeAssign(%s, %s)' % tuple(children)

    def visit_bind_assign(self, node, children):
        assert(len(children) == 2)
        return '%s(%s)' % tuple(children)

    def visit_function(self, node, children):
        if children[0] == 'not_implemented':
            return '// FIXME: not_implemented: %s' % children[1]

        if children[0] == 'SignExtend':
            return 'SignExtend<u%s, %s>(%s)' % (children[3], children[2], children[1])

        if children[0] == 'Expr::MakeId':
            return '%s(%s, &m_CpuInfo)' % (children[0], children[1])

        if children[0] == 'Expr::MakeVecId':
            return '%s(%s, &m_CpuInfo)' % (children[0], children[1])

        if children[0] == 'Expr::MakeMem':
            if len(children) == 3:
                return '%s(%s, nullptr, %s)' % tuple(children)
            return '%s(%s)' % tuple(children)

        if children[0] == 'Expr::MakeAssign':
            return '%s(%s, %s)' % (children[0], children[1], children[2])

        if children[0] == 'rInsn.AddAttribute':
            attr_flags = '%s_Attribute_%s' % (self._get_architecture_name().upper(), ''.join([x.capitalize() for x in children[1][1:-1].split(' ')]))
            return '%s(%s)' % (children[0], attr_flags)

        if children[0] == '__field':
            field_name = children[1][1:-1]
            if field_name[0] == '<' and field_name[-1] == '>':
                field_name = field_name[1:-1]
            extract_field = self._generate_extract_bits(field_name)
            if not extract_field:
                raise Exception('failed to generate extract field: %s' % field_name)
            return '%s /* %s */' % (extract_field, field_name)

        if children[0] == '__alloc_var':
            var_name = children[2][1:-1]
            var_bsz = children[1]
            self.var[var_name] = var_bsz
            return 'Expr::MakeVar("%s", VariableExpression::Alloc, %s)' % (var_name, var_bsz)

        if children[0] == '__free_var':
            var_name = children[1][1:-1]
            var_bsz = self.var[var_name]
            del self.var[var_name]
            return 'Expr::MakeVar("%s", VariableExpression::Free)' % (var_name)
            # return 'Expr::MakeVar("%s", VariableExpression::Free, %s)' % (var_name, var_bsz)

        if children[0] == '__bit_size':
            return '%s->GetBitSize()' % children[1]

        if children[0] == '__bit_cast':
            return 'Expr::MakeBinOp(OperationExpression::OpBcast, %s, %s)' % (children[1], children[2])

        if children[0] == 'm_CpuInfo.ConvertNameToIdentifier':
            id_name = children[1][1:-1]
            for registers in self.arch['register']:
                if id_name in registers.values()[0]:
                    return '%s_Reg_%s' % (self._get_architecture_name().upper(), id_name.capitalize())

        if children[0] == '__flt':
            return 'Expr::MakeBitVector(BitVector(%sf))' % (children[1])

        return '%s(%s)' % (children[0], ', '.join(children[1:]))

    def visit_if_else(self, node, children):
        if len(children) == 2:
            return 'if (%s)\n%s' % (children[0], indent(children[1]))
        assert(len(children) == 3)
        return 'if (%s)\n%s\nelse\n%s' % (children[0], children[1], children[2])

    def visit_when_block(self, node, children):
        assert(len(children) == 2)
        return 'case %s:\n%s%s' % (children[0], indent(children[1]), indent('break;'))

    def visit_case_when(self, node, children):
        assert(len(children) > 1)
        return 'switch (%s)\n{\n%s\n}' % (children[0], '\n'.join(children[1:]))

    def visit_conditional_statment(self, node, children):
        assert(len(children) == 1)
        return children[0]

    def visit_unconditional_statment(self, node, children):
        assert(len(children) == 1)
        return children[0] + ';'

    def visit_statment(self, node, children):
        assert(len(children) == 1)
        return children[0]

    def visit_block(self, node, children):
        if len(children) == 1:
            return indent(children[0])
        return '{\n%s\n}\n' % '\n'.join([ '  %s' % x for x in children ])

    def visit_code(self, node, children):
        return '\n'.join(children)


def main(debug = False):
    isabelle_grammar = open(os.path.join(os.path.dirname(__file__), 'isabelle.peg'), 'r').read()
    parser = ParserPEG(isabelle_grammar, 'code', debug = False)
    # parse_tree = parser.parse("...")
    # print parse_tree

if __name__ == '__main__':
    main(debug = False)
