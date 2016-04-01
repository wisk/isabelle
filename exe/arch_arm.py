from arch import ArchConvertion
from helper import *

import re
import sys
import string

sys.path.append('../parser')
from isabelle_parser import convert_decoder_to_medusa

class ArmArchConvertion(ArchConvertion):
    def __init__(self, arch):
        ArchConvertion.__init__(self, arch)
        self.arch = arch
        self.all_mnemo = set()

        self.id_mapper = {
        'nf':'ARM_FlNf','cf':'ARM_FlCf','vf':'ARM_FlVf','zf':'ARM_FlZf',
        'r0':'ARM_Reg0','r1':'ARM_Reg1','r2':'ARM_Reg2','r3':'ARM_Reg3',
        'r4':'ARM_Reg4','r5':'ARM_Reg5','r6':'ARM_Reg6','r7':'ARM_Reg7',
        'r8':'ARM_Reg8','r9':'ARM_Reg9','r10':'ARM_Reg10','r11':'ARM_Reg11',
        'r12':'ARM_Reg12','r13':'ARM_Reg13','r14':'ARM_Reg14','r15':'ARM_Reg15',
        'sp':'ARM_RegSP', 'lr':'ARM_RegLR', 'pc':'ARM_RegPC',
        }

        all_instructions = self.arch['instruction']

        self.arm_insns = []
        self.thumb_insns = []

        for insn in all_instructions:

            # Check if instruction is valid
            self._ARM_VerifyInstruction(insn)

            # Gather all mnemonics
            self.all_mnemo.add(self._ARM_GetMnemonic(insn).capitalize())

            if insn['mode'][0] == 'A':
                self.arm_insns.append(insn)
            elif insn['mode'][0] == 'T':
                self.thumb_insns.append(insn)

        self.arm_insns.sort(key=lambda insn: insn['encoding'])
        self.thumb_insns.sort(key=lambda insn: insn['encoding'])

    def _ARM_VerifyInstruction(self, insn):
        insn_sz = self._ARM_GetSize(insn)
        if insn_sz != 16 and insn_sz != 32:
            raise Exception('Invalid instruction "%s", encoding: %s, length: %d' % (insn['format'], insn['encoding'], insn_sz))

    def _ARM_Mangle(insn):
        encoding = []
        for bit in insn['encoding']:
            if type(bit) == int:
                encoding.append(str(bit))
            elif bit[0] == '(':
                encoding.append(bit[1])
            else:
                encoding.append(bit)
        return '%s_%s' % (insn['mode'], '_'.join(encoding))

    def _ARM_GetMnemonic(self, insn):
        fmt = insn['format']
        res = ''
        for c in fmt:
            if not c in string.ascii_letters+string.digits:
                break
            res += c
        return res

    def _ARM_GetMask(self, insn):
        enc = insn['encoding']
        res = 0x0
        off = 0x0
        for bit in enc[::-1]:
            if bit in [ '0', '1', '(0)', '(1)' ]:
                res |= (1 << off)

            if '#' in bit:
                off += int(bit.split('#')[1])
            else:
                off += 1
        return res

    def _ARM_GetValue(self, insn):
        enc = insn['encoding']
        res = 0x0
        off = 0x0
        for bit in enc[::-1]:
            if bit in [ '1', '(1)' ]:
                res |= (1 << off)

            if '#' in bit:
                off += int(bit.split('#')[1])
            else:
                off += 1
        return res

    def _ARM_GetSize(self, insn):
        enc = insn['encoding']
        insn_sz = 0
        for e in enc:
            if e in [ '0', '1', '(0)', '(1)' ]:
                insn_sz += 1
                continue

            if '#' in e:
                insn_sz += int(e.split('#')[1])
                continue

            raise Exception('Unable to get bit size of field: %s' % e)

        return insn_sz

    def _ARM_ExtractBits(self, insn, pattern):
        res = [] # beg, end
        enc = insn['encoding']
        beg = 0
        end = 0
        off = 0

        found = False
        for bitfield in enc[::-1]:
            if bitfield == pattern and not found:
                beg = off
                found = True
            elif bitfield != pattern and found:
                end = off - 1
                found = False
                res.append((beg, end))
            off += 1

        if end == 0 and enc[0] == pattern:
            end = len(enc) - 1
            res.append((beg, end))

        return res

    def _ARM_GenerateExtractBits(self, insn, pattern, scale = 0):
        bits = self._ARM_ExtractBits(insn, pattern)
        res = []

        zx_bit = 0
        off = 0
        for beg, end in bits:

            scale_str = ''
            if zx_bit != 0:
                scale_str = ' << %d' % zx_bit

            if beg == end:
                res.append('ExtractBit<%d>(Opcode)%s' % (beg, scale_str))
            else:
                res.append('ExtractBits<%d, %d>(Opcode)%s' % (beg, end, scale_str))

            zx_bit += end - beg + 1

        scale_str = ''
        if scale != 0:
            scale_str = ' << %d' % scale_str
        return '(%s)%s' % (' | '.join(res), scale_str)

    def _ARM_GenerateExtractBitsSigned(self, insn, pattern, scale = 0):
        bits = self._ARM_ExtractBits(insn, pattern)
        res = []

        sx_bit = 0
        off = 0
        for beg, end in bits:

            scale_str = ''
            if sx_bit != 0:
                scale_str = ' << %d' % sx_bit

            if beg == end:
                res.append('ExtractBit<%d>(Opcode)%s' % (beg, scale_str))
            else:
                res.append('ExtractBits<%d, %d>(Opcode)%s' % (beg, end, scale_str))

            sx_bit += end - beg + 1

        scale_str = ''
        if scale != 0:
            scale_str = ' << %d' % scale_str
        return 'SignExtend<s64, %d>(%s)%s' % (sx_bit, ' | '.join(res), scale_str)

    def _ARM_GenerateInstruction(self, insn):
        medusa_decoder = convert_decoder_to_medusa(self.arch, insn)
        if not medusa_decoder:
            raise Exception('failed to compile AST for: %s' % insn['format'])

        return self._ARM_GenerateMethodPrototype(insn, False) + '\n' + self._GenerateBrace(medusa_decoder + '\n')

    def _ARM_GenerateInstructionComment(self, insn):
        return '// %s - %s - %s\n' % (insn['format'], insn['attribute'], insn['encoding'])

    def _ARM_GenerateMethodName(self, insn):
        mnem  = self._ARM_GetMnemonic(insn)
        mode  = insn['mode']
        mask  = self._ARM_GetMask(insn)
        value = self._ARM_GetValue(insn)
        return 'Instruction_%s_%s_%08x_%08x' % (mnem, mode, mask, value)

    def _ARM_GenerateMethodPrototype(self, insn, in_class = False):
        mnem = self._ARM_GetMnemonic(insn)
        meth_fmt = 'bool %s(BinaryStream const& rBinStrm, TOffset Offset, u32 Opcode, Instruction& rInsn)'
        if in_class == False:
            meth_fmt = 'bool %sArchitecture::%%s(BinaryStream const& rBinStrm, TOffset Offset, u32 Opcode, Instruction& rInsn)' % self.GetArchName()

        return meth_fmt % self._ARM_GenerateMethodName(insn)

    def GenerateHeader(self):
        res = ''
        res += 'static char const *m_Mnemonic[%#x];\n' % (len(self.all_mnemo) + 1)

        for insn in sorted(self.arch['instruction'], key=lambda a:self._ARM_GetMnemonic(a)):
            res += self._ARM_GenerateMethodPrototype(insn, True) + ';\n'

        res += 'bool DisassembleArm(BinaryStream const& rBinStrm, TOffset Offset, Instruction& rInsn);\n'
        res += 'bool DisassembleThumb(BinaryStream const& rBinStrm, TOffset Offset, Instruction& rInsn);\n'

        return res

    def GenerateSource(self):
        res = ''

        res += 'bool ArmArchitecture::Disassemble(BinaryStream const& rBinStrm, TOffset Offset, Instruction& rInsn, u8 Mode)\n'
        res += self._GenerateBrace(
                'rInsn.GetData()->ArchitectureTag() = GetTag();\n'+
                'rInsn.Mode() = Mode;\n\n'+
                self._GenerateSwitch('Mode',
                    [('ARM_ModeArm',   'return DisassembleArm(rBinStrm, Offset, rInsn);\n',   False),
                     ('ARM_ModeThumb', 'return DisassembleThumb(rBinStrm, Offset, rInsn);\n', False)],
                    'return false;\n')
                )

        def _ARM_GenerateDispatcher(arm, insns):
            res = ''
            insns_dict = {}

            # regroup instructions with the same mask
            for insn in insns:
                mask = arm._ARM_GetMask(insn)
                if not mask in insns_dict:
                    insns_dict[mask] = []
                insns_dict[mask].append(insn)

            # order by number of 0 and 1 in order to handle alias correctly
            def get_bit_count(elem):
                return 32 - bin(elem[0]).count('1')
            insns_list = sorted(insns_dict.items(), key=get_bit_count)

            for mask, insn_list in insns_list:
                bit = self._ARM_GetSize(insn_list[0])
                if len(insn_list) == 1:
                    value = arm._ARM_GetValue(insn_list[0])
                    res += arm._GenerateCondition('if', '(Opcode%d & %#010x) == %#010x' % (bit, mask, value), self._ARM_GenerateInstructionComment(insn_list[0]) + 'return %s(rBinStrm, Offset, Opcode%d, rInsn);' % (arm._ARM_GenerateMethodName(insn_list[0]), bit))
                else:
                    cases = []
                    for insn in insn_list:
                        value = arm._ARM_GetValue(insn)
                        cases.append( ('%#010x' % value, self._ARM_GenerateInstructionComment(insn) + 'return %s(rBinStrm, Offset, Opcode%d, rInsn);\n' % (arm._ARM_GenerateMethodName(insn), bit), False) )
                    res += arm._GenerateSwitch('Opcode%d & %#010x' % (bit, mask), cases, 'break;\n')

            return res

        res += 'bool ArmArchitecture::DisassembleArm(BinaryStream const& rBinStrm, TOffset Offset, Instruction& rInsn)\n'
        res += self._GenerateBrace(
                self._GenerateRead('Opcode32', 'Offset', 32)+
                _ARM_GenerateDispatcher(self, self.arm_insns)+
                'return false;\n'
                )

        res += 'bool ArmArchitecture::DisassembleThumb(BinaryStream const& rBinStrm, TOffset Offset, Instruction& rInsn)\n'
        res += self._GenerateBrace(
                self._GenerateRead('Opcode16Low', 'Offset & ~1', 16)+
                self._GenerateRead('Opcode16High', '(Offset + 2) & ~1', 16)+
                Indent('u16 Opcode16 = Opcode16Low;\n', 0)+
                Indent('u32 Opcode32 = ((Opcode16Low << 16) | Opcode16High);\n', 0)+
                _ARM_GenerateDispatcher(self, self.thumb_insns)+
                'return false;\n'
                )

        for insn in self.arm_insns + self.thumb_insns:
            res += self._ARM_GenerateInstructionComment(insn)
            res += self._ARM_GenerateInstruction(insn)

        return res

    def GenerateOpcodeEnum(self):
        res = ',\n'.join('ARM_Opcode_%s' % x.capitalize() for x in ['unknown'] + sorted(self.all_mnemo)) + '\n'
        return 'enum ARM_Opcode\n' + self._GenerateBrace(res)[:-1] + ';\n'

    def GenerateOpcodeString(self):
        res = ',\n'.join('"%s"' % x.lower() for x in ['unknown'] + sorted(self.all_mnemo)) + '\n'
        return 'const char *%sArchitecture::m_Mnemonic[%#x] =\n' % (self.GetArchName(), len(self.all_mnemo) + 1) + self._GenerateBrace(res)[:-1] + ';\n'

    def GenerateOperandDefinition(self):
        res = ''
        return res

    def GenerateOperandCode(self):
        res = ''
        return res
