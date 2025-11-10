import os, zipfile
import xml.sax.saxutils as sax

def xml_escape(s: str) -> str:
    return sax.escape(s, {'"': '&quot;', "'": '&apos;'})

# --- DOCX minimal ---
def write_docx(text: str, path: str):
    lines = text.splitlines()
    body = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">',
            '  <w:body>']
    for ln in lines:
        if ln.strip() == '':
            body.append('    <w:p/>')
        else:
            body.append(f'    <w:p><w:r><w:t xml:space="preserve">{xml_escape(ln)}</w:t></w:r></w:p>')
    body += ['    <w:sectPr/>','  </w:body>','</w:document>']
    document_xml = "\n".join(body)
    content_types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
                     '  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
                     '  <Default Extension="xml" ContentType="application/xml"/>\n'
                     '  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>\n'
                     '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
            '  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>\n'
            '</Relationships>')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', content_types)
        z.writestr('_rels/.rels', rels)
        z.writestr('word/document.xml', document_xml)

# --- XLSX minimal ---

def a1(col_idx: int, row_idx: int) -> str:
    col = ''
    n = col_idx
    while n:
        n, r = divmod(n-1, 26)
        col = chr(65+r) + col
    return f"{col}{row_idx}"

def write_xlsx(rows, path: str):
    content_types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
                     '  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
                     '  <Default Extension="xml" ContentType="application/xml"/>\n'
                     '  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>\n'
                     '  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>\n'
                     '</Types>')
    rels_pkg = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
                '  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>\n'
                '</Relationships>')
    workbook = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">\n'
                '  <sheets>\n'
                '    <sheet name="Schedule" sheetId="1" r:id="rId1"/>\n'
                '  </sheets>\n'
                '</workbook>')
    rels_wb = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
               '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
               '  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>\n'
               '</Relationships>')
    sheet_lines = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
                   '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
                   '  <sheetData>']
    for i, row in enumerate(rows, start=1):
        sheet_lines.append(f'    <row r="{i}">')
        for j, val in enumerate(row, start=1):
            v = '' if val is None else str(val)
            sheet_lines.append(f'      <c r="{a1(j,i)}" t="inlineStr"><is><t>{xml_escape(v)}</t></is></c>')
        sheet_lines.append('    </row>')
    sheet_lines += ['  </sheetData>','</worksheet>']
    sheet_xml = "\n".join(sheet_lines)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', content_types)
        z.writestr('_rels/.rels', rels_pkg)
        z.writestr('xl/workbook.xml', workbook)
        z.writestr('xl/_rels/workbook.xml.rels', rels_wb)
        z.writestr('xl/worksheets/sheet1.xml', sheet_xml)

# --- Rulebook text (v0.3 adds camera & HUD/log) ---
rulebook = '''2D 战车竞技场 规则书 v0.3（增补：摄像头与HUD/日志）
日期：11/10

【沿用 v0.2 内容略】

十二、摄像头与可读性规范（当前采用方案 A：全场固定视角）
- 模式：一屏容纳整个房间/战场；BOSS 房同理为“一屏大小”。
- 公平性与可读性：
  1) 生成器保证出生点安全区（半径≥2格）且不在玩家身边瞬刷；
  2) 敌人/危害具有明显电告与轨迹（AOE 地面高亮、火箭图标/音效提示）；
  3) 软锁目标高亮，锁定对象在 HUD 显示名称/血量条；
  4) 子弹速度、霰弹散布、火箭溅射半径保持“所见即所得”；
  5) UI 层级：受击、过量伤害、冲刺与技能 CD 清晰可读。
- 未来方案评估（第二周进行决策）：
  - B：跟随摄像头（有限视角）需配套：边缘指示、出生电告、最小刷怪距离、小地图/雷达（可选）；
  - C：战斗/ BOSS 自动轻微拉远；
  - D：房间制镜头跳转（每房一屏）。
  - 当前版本默认维持 A，评估结论以排期节点为准。

十三、日志 / HUD 规范（可热键开关）
- CSV 日志（默认开启，可 F2 开关）
  - 路径：logs/session_YYYYMMDD_HHMMSS.csv；回合结束写 1 行聚合数据。
  - 字段建议：
    run_id, seed, round_index, room_id, tile_mix_normal, tile_mix_mud, tile_mix_ice, obstacle_density,
    time_to_clear, player_hp_end, armor_end, damage_dealt, damage_taken,
    weapon_type, weapon_quality, ammo_mod, shots_fired, shots_hit, hit_rate,
    reload_count, sprint_uses, skill_uses,
    collisions_triggered, collision_kills,
    enemy_count, enemy_types, ai_profile_version,
    reward_offers, reward_chosen, currency_gained, repairs_used
  - 事件日志（可选第二张 CSV）：t, event_type, v1..vN（spawn/skill_fire/boss_phase_change 等）。
- 开发 HUD（F1 开关）
  - 显示：FPS、回合/波次、计时(time_to_clear)、HP/Armor、弹匣与换弹、命中率滚动、
          冲刺/技能 CD、当前软锁目标、脚下地形系数、碰撞阈值提示。
  - 调试叠加（F3 开关）：出生点与安全区圈、敌/玩家 hitbox、子弹轨迹、AI 目标点。
  - 发布版默认关闭上述开关。'''

# --- Schedule rows v2 (add camera evaluation in week 2) ---
schedule = [
    ['Date','Day','Milestone','Focus','Key Deliverables','Notes'],
    ['11/10','D2','规则书 v0.2→v0.3 增补','设计','加入摄像头与HUD/日志规范；排期锁定','当前使用摄像头方案A'],
    ['11/11','D3','MVP v0.1','核心玩法','移动/冲刺/软锁；机枪（白绿紫）；清场即胜','近战“冲撞板”基础判定'],
    ['11/12','D4','武器与护甲','战斗','火箭；霰弹占位；护甲第二血（脱战回）；武装受损降速/精度','HUD 初版'],
    ['11/13','D5','回合与奖励','循环','波次（2–6 敌）；回合后 3 选 1（含维修包/弹药/零件/资源）',''],
    ['11/14','D6','场景生成 AI v0','关卡','障碍/出生点/安全区；普通/泥/冰占比（线性+轻微自适）','回合 30–60s'],
    ['11/15','D7','垂直切片 v0.5','流程','3 回合→BOSS 框架（核心可破）→结算','霰弹手感补强'],
    ['11/16','D8','功能收束与埋点','工具','CSV 日志/事件流；HUD/调试叠加开关',''],
    ['11/17','D9','测试基线采集 A','测试','10+ 局灰盒数据；AI阈值初调；场景密度回归',''],
    ['11/18','D10','奖励推荐 A','优化','三选一加权（补短板/武器匹配）；回归测试',''],
    ['11/19','D11','敌人 AI 细化','优化','近战卡角/冲撞窗口；远程保距/换位；线性曲线重标',''],
    ['11/20','D12','场景 AI v1','优化','地形占比与障碍组合模板+权重；避免极端布局',''],
    ['11/21','D13','摄像头方案评估与决策','体验/可读','A vs B/C/D 指标对比与结论；如过渡列配套清单','当前默认维持 A'],
    ['11/22','D14','数据复盘与数值回归','平衡','对齐时长/受击率/命中率；冻结 AI 参数 v1',''],
    ['11/23','D15','集成演练','流程','整条流程打穿；缺口清单出炉','进入资源整合阶段'],
    ['11/24','D16','美术整合 A','资源','替换占位，统一 UI/HUD；命中/提示特效',''],
    ['11/25','D17','音效与混音','资源','武器/命中/受击/预警；距离衰减与压限',''],
    ['11/26','D18','性能与内存 B','优化','对象池/空间哈希/回收；加载复用审计',''],
    ['11/27','D19','全面测试 RC1','验收','功能/回归/压力；问题燃尽单',''],
    ['11/28','D20','修复与平衡收束 RC2','验收','关键 BUG/数值微调；发版脚本',''],
    ['11/29','D21','最终整合与发布','发行','发行页素材；版本封板；回滚方案','']
]

os.makedirs('docs', exist_ok=True)
write_docx(rulebook, os.path.join('docs','规则书_v0.3.docx'))
write_xlsx(schedule, os.path.join('docs','时间安排_v2.xlsx'))
print('OK v0.3/v2 written')
