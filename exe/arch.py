from helper import *

import ast, time, sys

sys.path.append('../parser')
from isabelle_parser import convert_function_to_medusa

class ArchConvertion:
    def __init__(self, arch):
        self.arch = arch

    def GetArchName(self):
        return self.arch['name'].capitalize()

    def GenerateBanner(self):
        return '/* This file has been automatically generated, you must _NOT_ edit it directly. (%s) */\n' % time.ctime()

    # Private methods
    def _GenerateBrace(self, code):
        return '{\n' + Indent(code) + '}\n'

    def _GenerateCondition(self, cond_type, cond, statm):
        res = ''

        if cond != None:
            res += '%s (%s)\n' % (cond_type, cond)
        else:
            res += '%s\n' % (cond_type)

        if statm[-1] != '\n':
            res += Indent(statm + '\n')
        else:
            res += self._GenerateBrace(statm)
        return res

    def _GenerateSwitch(self, cond, cases, default):
        res = ''

        res += 'switch (%s)\n' % cond
        res += '{\n'
        for case in cases:
            res += 'case %s:\n' % case[0]
            res += Indent(case[1])
            if case[2]: res += Indent('break;\n')
        res += 'default:\n'
        res += Indent('%s' % default)
        res += '}\n'
        return res

    def _GenerateRead(self, var_name, addr, sz):
        return 'u%d %s;\nif (!rBinStrm.Read(%s, %s))\n  return false;\n\n' % (sz, var_name, addr, var_name)

    def GenerateHeader(self):
        pass

    def GenerateSource(self):
        pass

    def GenerateFunction(self):
        res = ''

        for f in self.arch['function']:
            f_name = f['name']
            f_parm = f['parameter']
            f_code = f['code']

            res += '/* parameter: %s */\n' % f_parm
            res += 'void %s(Instruction& rInsn, CpuInformation& m_CpuInfo)\n' % f_name # FIXME(wisk): m_CpuInfo doesn't respect the coding convention
            res += self._GenerateBrace(convert_function_to_medusa(self.arch, f_code, f_parm))
            res += '\n'

        return res

    def GenerateOpcodeEnum(self):
        pass

    def GenerateOpcodeString(self):
        pass

    def GenerateOperandDefinition(self):
        pass

    def GenerateOperandCode(self):
        pass
