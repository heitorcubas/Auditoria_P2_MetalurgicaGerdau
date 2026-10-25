"""Gera Papeis_de_trabalho_calculos.xlsx (PT 320, PT 530, PT 450).
Uso: python gerar_planilha_v6.py   |   Dependência: openpyxl
Valores do PT 530 copiados do print de gerar_base_v5.py (seed 2025) — coluna 'Líquido Contábil (C−D)',
que fecha com a Nota 10.a (R$ 30.641.058.000,00).
"""
import os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

MOEDA = '"R$" #,##0.00;("R$" #,##0.00);"-"'
INT = '#,##0;(#,##0);"-"'
F = 'Arial'
AZUL, PRETO = '0000FF', '000000'
HEAD = PatternFill('solid', fgColor='1F4E5A')
THIN = Border(bottom=Side(style='thin', color='BFBFBF'))


def aba(wb, nome, titulo, cab, linhas, larg, fmt):
    ws = wb.create_sheet(nome)
    ws.sheet_view.showGridLines = False
    ws['A1'] = titulo
    ws['A1'].font = Font(name=F, size=14, bold=True, color='1F4E5A')
    ws['A2'] = 'Metalúrgica Gerdau S.A. | Exercício 2025 | Valores em R$'
    ws['A2'].font = Font(name=F, size=9, italic=True, color='595959')
    ws.append([])
    ws.append(cab)
    for c in ws[4]:
        c.font = Font(name=F, bold=True, color='FFFFFF'); c.fill = HEAD
        c.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
    for l in linhas:
        ws.append(l)
    for row in ws.iter_rows(min_row=5, max_row=ws.max_row):
        for c in row:
            f = isinstance(c.value, str) and c.value.startswith('=')
            num = isinstance(c.value, (int, float))
            c.font = Font(name=F, color=AZUL if num else PRETO, bold=str(ws.cell(c.row, 1).value).startswith('Total'))
            c.border = THIN
            if c.column in fmt:
                c.number_format = fmt[c.column]
            c.alignment = Alignment(horizontal='right' if (f or num) else 'left', vertical='center', wrap_text=True)
    for i, w in enumerate(larg, 1):
        ws.column_dimensions[chr(64 + i)].width = w
    ws.row_dimensions[4].height = 34
    return ws


wb = Workbook(); wb.remove(wb.active)

# PT 320 — Materialidade
ws = aba(wb, 'PT 320', 'PT 320 — Determinação da Materialidade',
         ['Item', 'Base / %', 'Valor (R$)'],
         [['LAIR (Lucro antes do IR/CS)', None, 2519769000.00],
          ['Materialidade Global (MG)', 0.05, '=C5*B6'],
          ['Materialidade de Execução (ME)', 0.70, '=C6*B7'],
          ['Limite de Distorção Clara/Trivial (SUD)', 0.05, '=C6*B8']],
         [44, 12, 22], {2: '0.0%', 3: MOEDA})

# PT 530 — Amostragem por estratos
ws = aba(wb, 'PT 530', 'PT 530 — Amostragem Estratificada do Imobilizado',
         ['Estrato', 'Tamanho da População', 'Valor Populacional (R$)', 'Tamanho da Amostra', 'Técnica', 'Intervalo / Fator Poisson (R$)'],
         [['Estrato 1 — Máquinas adquiridas em dez/2025', 3060, 534009193.02, 3060, 'Teste 100% (censo)', None],
          ['Estrato 2A — TI restante', 49500, 195225000.00, 200, 'Amostragem estatística', None],
          ['Estrato 2B — TI 100% depreciado (CAAT)', 500, 0.00, 500, 'CAAT — 100% das linhas', None],
          ['Estrato 3 — Demais ativos', 451940, 29911823806.98, 150, 'MUS — Poisson (fator 3,0)', '=(C8*3.0)/D8'],
          ['Total', '=SUM(B5:B8)', '=SUM(C5:C8)', '=SUM(D5:D8)', None, None],
          ['Checagem: população = 505.000 e valor = Nota 10.a', '=IF(B9=505000,"OK","ERRO")', '=IF(ROUND(C9,2)=30641058000,"OK","ERRO")', None, None, None]],
         [46, 16, 24, 14, 26, 24], {2: INT, 3: MOEDA, 4: INT, 6: MOEDA})

# PT 450 — Distorções identificadas
ws = aba(wb, 'PT 450', 'PT 450 — Sumário de Distorções Identificadas',
         ['Ref.', 'Descrição', 'Distorção Bruta (R$)', 'Alíquota IR/CS', 'Efeito Líquido no Resultado (R$)'],
         [['D1', 'Máquinas dez/2025: Valor Líquido = 5,0x o Custo (200 ativos)', 168201896.33, 0.34, '=-C5*(1-D5)'],
          ['D2', 'TI 100% depreciado registrado a 50% do custo (500 ativos)', 29393724.47, 0.34, '=-C6*(1-D6)'],
          ['Total', None, '=SUM(C5:C6)', None, '=SUM(E5:E6)'],
          ['vs. ME', "='PT 320'!C7", '=IF(C7>B8,"Acima da ME — relevante","Abaixo da ME")', None, None]],
         [10, 58, 22, 14, 26], {2: MOEDA, 3: MOEDA, 4: '0%', 5: MOEDA})
ws['B8'].number_format = MOEDA

out = 'Papeis_de_trabalho_calculos.xlsx'
if os.path.exists(out):
    os.remove(out)
wb.save(out)
print('Gerado:', out)
