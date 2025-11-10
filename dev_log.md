**开发日志**



📅*2025-11-09*

**今日完成**

    项目初始化：仓库、虚拟环境、codex、基础 loop（arcade 窗口、场景状态机）、灰盒地图（20×15）
    
    数据驱动骨架：data/ 下 JSON（parts.json、weapons.json、enemies.json、waves.json、tiles.json）
    
    定义调参面板与调试覆盖层

    完成规则书与企划书初稿

    初始化项目仓库并上传到 GitHub

    完成玩家控制系统的编写，支持上下左右移动

**遇到问题与解决**

Arcade 模块无法导入

    通过创建虚拟环境并激活环境解决依赖问题

地图加载出现错误，背景色无法正确显示

    检查初始化 Sprite 的顺序，并修复 draw 方法调用顺序

**明日计划**

    规则书/企划书定稿
    
    完成数据表内容固化
    
    资源占位与 Player 控制器雏形实现（推力、最大速、转向力、抓地力四参数）

---

📅2025-11-11

**今日完成**

    抓地/惯性预设系统：新增并启用 medium/mud/ice 三套预设（含最高速/抓地/滚阻/侧滑收敛/低速截断）
    
    预设热键与 HUD：7=medium、9=ice、0=mud，HUD 显示当前 Grip 模式
    
    Dash 余势回归：加入 dash_decay + dash_transfer，将冲刺剩余速度逐步并入基础速度，冰面更长滑、泥地更快回归
    
    方向输入稳定化：补齐 on_key_release 清理按键、修正“粘键/锁死”；顶墙判定阈值微调（blocked_ratio≈0.40）
    
    机枪弹药数值调整：
    white: damage 3.0 / mag 24 / fire_rate 3.0 / reload 1.8
    green: damage 4.0 / mag 30 / fire_rate 3.3 / reload 1.6
    purple: damage 5.0 / mag 36 / fire_rate 3.9 / reload 1.4
    
    运行验证：本地编译通过；基础移动与冲刺在三套预设下手感差异明显（更黏/更滑）

**遇到问题与解决**

移动“滑行/锁死”问题

    原因：未清理按键集合（松开后仍判定按下），以及速度模型缺乏滚阻/抓地控制
    解决：on_key_release 丢弃按键；加入 traction/roll friction/drag/steer align/min_speed_cut；挡墙清零相应轴速度
    
冲刺易“瞬断”

    原因：dash 与基础速度融合不足
    解决：按预设将 dash 速度按秒率并入 move_vel，并保持独立的指数衰减，形成顺势滑行
    
手感调参效率低

    解决：添加热键切换预设 + HUD 显示 Grip 模式，便于现场微调与对比

**明日计划**

    加入火箭、霰弹两种新的武器，机枪微调并调整初始精度

    设计护甲系统

    设计武器血量系统（受损降速/精确度下降）

---
