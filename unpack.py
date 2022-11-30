# 本模块将二进制数据包解包为结构化数据
# 参考协议：
# 1. `IEC 60870-5-101` (传输规约基本远动任务配套标准)
# 2. `GB/T 18657.4-2002` (应用信息元素的定义和编码)
from math import log2
from struct import unpack

from data import *
from iec_types import APDU, ASDU


################################ 数值解析 ################################
def unpack_info_obj_addr(data: bytes):
    """解析 地址信息"""
    return unpack('<I', data + (4 - len(data)) * b'\x00')[0]


def unpack_Q(data: int):
    """品质描述词公有信息"""
    qual = []
    if data & 0b10000:
        qual.append('BL')
    if data & 0b100000:
        qual.append('SB')
    if data & 0b1000000:
        qual.append('NT')
    if data & 0b10000000:
        qual.append('IV')
    return qual


# 7.2.6.1
def unpack_SIQ(data: int):
    """解析 带品质描述词的单点信息"""
    SIQ = unpack_Q(data)
    if data & 0b1:
        SIQ.append('SPI')
    return SIQ


# 7.2.6.2
def unpack_DIQ(data: int):
    """解析 带品质描述词的双点信息"""
    DIQ = unpack_Q(data)
    DIQ.append(('不确定或中间状态', '确定状态开', '确定状态合', '不确定')[data & 0b11])
    return DIQ


# 7.2.6.3
def unpack_QDS(data: int):
    """解析 品质描述词"""
    QDS = unpack_Q(data)
    if data & 0b1:
        QDS.append('OV')
    return QDS


# 7.2.6.4
def unpack_QDP(data: int):
    """解析 继电保护设备事件的品质描述词"""
    QDP = unpack_Q(data)
    if data & 0b1:
        QDP.append('EI')
    return QDP


# 7.2.6.5
def unpack_VTI(data: int):
    """解析 带瞬变状态指示的值"""
    val = data & 0b1111111  # 取后七位
    val <<= 1  # 左移一位
    val = unpack('b', val)[0]  # 以有符号单字节整型解析
    val >>= 1  # 右移一位
    return {
        '值': val, 
        '瞬变状态': '设备处于瞬变状态' if data & 0b1 else '设备未在瞬变状态', 
    }


# 7.2.6.6
def unpack_NVA(data: bytes):
    """解析 规一化值"""
    if data[0] & 0b10000000 == 0b10000000:
        # 标志位为1时
        if data[0] == 0b10000000 and data[1] == 0b0:
            return -1
        else:
            return unpack('>H', data) / 32768
    else:
        # 标志位为0时
        return unpack('>H', data) / 32768


# 7.2.6.7
def unpack_SVA(data: bytes):
    """解析 标度化值"""
    return unpack('>h', data)[0]


# 7.2.6.8
def unpack_float32(data: bytes):
    """解析 短浮点数 (短浮点数定义于IEEE 754)"""
    return unpack('<f', data)[0]  # 标准定义直接解析即可


# 7.2.6.9
def unpack_BCR(data: bytes):
    """解析 二进制计数器读数"""
    I32 = data[:4]
    CP8 = data[4]
    return {
        '计数器读数': unpack('<i', I32), 
        '顺序号': unpack('B', CP8 & 0b11111), 
        '进位': '计数器溢出' if CP8 & 0b100000 else '计数器未溢出', 
        '计数量是否被调整': '计数器被调整' if CP8 & 0b1000000 else '计数器未被调整', 
        '有无效': '无效' if CP8 & 0b10000000 else '有效', 
    }


# 7.2.6.10
def unpack_SEP(data: int):
    """解析 继电保护设备单个事件"""
    SEP = unpack_Q(data)
    SEP.append(('不确定或中间状态', '确定状态开', '确定状态合', '不确定')[data & 0b11])
    if data & 0b1000:
        SEP.append('EI')
    return SEP


# 7.2.6.11
def unpack_SPE(data: int):
    """解析 继电保护设备启动事件"""
    return {
        '总启动': '总启动' if data & 0b1 else '无总启动', 
        '总启动': 'A相保护启动' if data & 0b10 else 'A相保护未启动', 
        '总启动': 'B相保护启动' if data & 0b100 else 'B相保护未启动', 
        '总启动': 'C相保护启动' if data & 0b1000 else 'C相保护未启动', 
        '总启动': '接地电流保护启动' if data & 0b10000 else '接地电流保护未启动', 
        '总启动': '反向保护启动' if data & 0b100000 else '反向保护未启动', 
    }


# 7.2.6.12
def unpack_OCI(data: int):
    """解析 继电保护设备输出电路信息"""
    return {
        '总命令输出至输出电路': '总命令输出至输出电路' if data & 0b1 else '无总命令输出至输出电路', 
        'A相保护命令输出至输出电路': '命令输出至A相输出电路' if data & 0b10 else '无命令输出至A相输出电路', 
        'B相保护命令输出至输出电路': '命令输出至B相输出电路' if data & 0b100 else '无命令输出至B相输出电路', 
        'C相保护命令输出至输出电路': '命令输出至C相输出电路' if data & 0b1000 else '无命令输出至C相输出电路', 
    }


# 7.2.6.13
def unpack_BSI(data: bytes):
    """解析 二进制状态信息"""
    return ''.join([bin(data[i]).strip('0b') for i in range(4)])


# 7.2.6.14
def unpack_FBP(data: bytes):
    """解析 固定测试字，两个八位位组"""
    return unpack('<H', data)[0]


# 7.2.6.15
def unpack_SCO(data: int):
    """解析 单命令"""
    return {
        '单命令状态': '合' if data & 0b1 else '开', 
        '命令限定词': unpack_QOC(data), 
    }


# 7.2.6.16
def unpack_DCO(data: int):
    """解析 双命令"""
    return {
        '双命令状态': ('不允许', '开', '合', '不允许')[data & 0b11], 
        '命令限定词': unpack_QOC(data)
    }


# 7.2.6.17
def unpack_RCO(data: int):
    """解析 步调节命令"""
    return {
        '步调节命令状态': ('不允许', '降一步', '升一步', '不允许')[data & 0b11], 
        '命令限定词': unpack_QOC(data)
    }


# 7.2.6.18
def unpack_CP56Time2a(data: bytes):
    """解析 七个八位位组二进制时间 该时间为增量时间信息，其增量的参考日期协商确定"""
    cp56time = unpack_CP24Time2a(data[:3])
    cp56time['hour'] = data[3] & 0b11111
    cp56time['st'] = data[3] & 0b10000000
    cp56time['day'] = data[4] & 0b11111
    cp56time['weekday'] = data[4] & 0b11100000
    cp56time['month'] = data[5] & 0b1111
    cp56time['year'] = data[6] & 0b1111111
    return cp56time


# 7.2.6.19
def unpack_CP24Time2a(data: bytes):
    """解析 三个八位位组二进制时间 该时间为增量时间信息，其增量的参考日期协商确定"""
    return {
        'seconds': unpack_CP16Time2a(data), 
        'minutes': data[2] & 0b111111, 
        'IV': True if data[2] & 0b10000000 else False,  # 有效无效
    }


# 7.2.6.20
def unpack_CP16Time2a(data: bytes):
    """解析 二个八位位组二进制时间 该时间为增量时间信息，其增量的参考日期协商确定"""
    return unpack('<H', data)[0] / 1000  # 单位：秒(s)


# 7.2.6.21
def unpack_COI(data: int):
    """解析 初始化原因"""
    UI7 = data & 0b1111111
    BS1 = data & 0b10000000
    if UI7 == 0:
        init_reason = '当地电源合上'
    elif UI7 == 1:
        init_reason = '当地手动复位'
    elif UI7 == 2:
        init_reason = '远方复位'
    elif 3 <= UI7 <= 31:
        init_reason = '标准定义初始化原因%s' % UI7
    elif 32 <= UI7 <= 127:
        init_reason = '特定初始化原因%s' % UI7
    return {
        '初始化原因': init_reason, 
        '类型': '改变当地参数后的初始化' if BS1 else '未改变当地参数后的初始化', 
    }


# 7.2.6.22
def unpack_QOI(data: int):
    """解析 召唤限定词"""
    UI8 = data
    if UI8 == 0:
        return '未用'
    elif 1<= UI8 <= 19:
        return '本配套标准定义召唤限定词%s' % UI8
    elif UI8 == 20:
        return '站召唤（全局）'
    elif 21 <= UI8 <= 36:
        return '第%s组召唤' % (UI8 - 20)
    elif 37 <= UI8 <= 63:
        return '配套标准定义召唤限定词%s' % UI8
    elif 64 <= UI8 <= 255:
        return '特定召唤限定词%s' % UI8


# 7.2.6.23
def unpack_QCC(data: int):
    """解析 计数量召唤命令限定词"""
    RQT = data & 0b111111
    if RQT == 0:
        req = '未采用请求计数量'
    elif 1 <= RQT <= 4:
        req = '请求计数量第%s组' % RQT
    elif RQT == 5:
        req = '总的请求计数量'
    elif 6 <= RQT <= 31:
        req = '标准计数量命令召唤限定词%s' % RQT
    elif 32 <= RQT <= 63:
        req = '特定计数量命令召唤限定词%s' % RQT
    return {
        '请求': req, 
        '冻结': ('读', '计数量冻结不带复位', '计数量冻结带复位', '计数量复位')[(data & 0b11000000) >> 6]
    }


# 7.2.6.24
def unpack_QPM(data: int):
    """解析 测量值参数限定词"""
    KPA = data & 0b111111
    LPC = data & 0b1000000
    POP = data & 0b10000000
    if KPA == 0:
        kpa = '未用'
    elif KPA == 1:
        kpa = '门限值'
    elif KPA == 2:
        kpa = '平滑系数（滤波时间常数）'
    elif KPA == 3:
        kpa = '传送测量值的下限'
    elif KPA == 4:
        kpa = '传送测量值的上限'
    elif 5 <= KPA <= 31:
        kpa = '标准测量值参数限定词%s' % KPA
    elif 32 <= KPA <= 63:
        kpa = '特定测量值参数限定词%s' % KPA
    return {
        '参数类别': kpa, 
        '当地参数改变': '改变' if LPC else '未改变', 
        '参数在运行': '未运行' if POP else '运行', 
    }


# 7.2.6.25
def unpack_QPA(data: int):
    """解析 参数激活限定词"""
    QPA = data
    if QPA == 0:
        return '未用'
    elif QPA == 1:
        return '激活/停止激活之前装载的参数(信息对象地址=0)'
    elif QPA == 2:
        return '激活/停止激活所寻址信息对象的参数'
    elif QPA == 3:
        return '激活/停止激活所寻址的持续循环或周期传输的信息对象'
    elif 4 <= QPA <= 127:
        return '标准参数激活限定词%s' % QPA
    elif 128 <= QPA <= 255:
        return '特定参数激活限定词%s' % QPA


# 7.2.6.26
def unpack_QOC(data: int):
    """解析 命令限定词"""
    QU = (data & 0b01111100) >> 2
    if QU == 0:
        qu = '无另外的定义'
    elif QU == 1:
        qu = '短脉冲持续时间，持续由被控站内系统参数所确定'
    elif QU == 2:
        qu = '长脉冲持续时间，持续由被控站内系统参数所确定'
    elif QU == 3:
        qu = '持续输出'
    elif 4 <= QU <= 8:
        qu = '标准定义%s(兼容)' % QU
    elif 9 <= QU <= 15:
        qu = '预定义功能%s' % QU
    elif 16 <= QU <= 31:
        qu = '特定功能%s(专用)' % QU
    return {'命令限定词': qu, '选择/执行': '选择' if data & 0b10000000 else '执行'}


# 7.2.6.27
def unpack_QRP(data: int):
    """解析 复位进程命令限定词"""
    QRP = data
    if QRP == 0:
        return '未采用'
    elif QRP == 1:
        return '进程的总复位'
    elif QRP == 2:
        return '复位事件缓冲区等待处理的带时标的信息'
    elif 3 <= QRP <= 127:
        return '标准复位进程命令限定词%s' % QRP
    elif 128 <= QRP <= 255:
        return '特定复位进程命令限定词%s' % QRP


# 7.2.6.28
def unpack_FRQ(data: int):
    """解析 文件准备就绪限定词"""
    FRQ = data & 0b1111111
    BS1 = data & 0b10000000
    if FRQ == 0:
        frq = '缺省'
    elif 1 <= FRQ <= 63:
        frq = '标准文件准备就绪限定词%s' % FRQ
    elif 64 <= FRQ <= 127:
        frq = '特定文件准备就绪限定词%s' % FRQ
    return {
        '文件准备就绪限定词': frq, 
        '肯定/否定确认': '选择、请求、停止激活或删除的否定确认' if BS1 else '选择、请求、停止激活或删除的肯定确认', 
    }


# 7.2.6.29
def unpack_SRQ(data: int):
    """解析 节准备就绪限定词"""
    SRQ = data & 0b1111111
    BS1 = data & 0b10000000
    if SRQ == 0:
        srq = '缺省'
    elif 1 <= SRQ <= 63:
        srq = '标准节准备就绪限定词%s' % SRQ
    elif 64 <= SRQ <= 127:
        srq = '特定节准备就绪限定词%s' % SRQ
    return {
        '节准备就绪限定词': srq, 
        '节已/未准备就绪': '节未准备就绪' if BS1 else '节准备就绪', 
    }


# 7.2.6.30
def unpack_SCQ(data: int):
    """解析 选择和召唤限定词"""
    Word = data & 0b1111
    Err = (data & 0b11110000) >> 4
    if Word == 0:
        w = '缺省'
    elif Word == 1:
        w = '选择文件'
    elif Word == 2:
        w = '请求文件'
    elif Word == 3:
        w = '停止激活文件'
    elif Word == 4:
        w = '删除文件'
    elif Word == 5:
        w = '选择节'
    elif Word == 6:
        w = '请求节'
    elif Word == 7:
        w = '停止激活节'
    elif 8 <= Word <= 10:
        w = '标准限定词%s' % Word
    elif 11 <= Word <= 15:
        w = '特定限定词%s' % Word
    
    if Err == 0:
        e = '缺省'
    elif Err == 1:
        e = '无请求的存储空间'
    elif Err == 2:
        e = '校验和错'
    elif Err == 3:
        e = '非所期望的通信服务'
    elif Err == 4:
        e = '非所期望的文件名称'
    elif Err == 5:
        e = '非所期望的节名称'
    elif 6 <= Err <= 10:
        e = '标准错误%s' % Err
    elif 11 <= Err <= 15:
        e = '特定错误%s' % Err
    return {'限定词': w, '错误信息': e}


# 7.2.6.31
def unpack_LSQ(data: int):
    """解析 最后的节和段的限定词"""
    LSQ = data
    if LSQ == 0:
        return '未用'
    elif LSQ == 1:
        return '不带停止激活的文件传输'
    elif LSQ == 2:
        return '带停止激活的文件传输'
    elif LSQ == 3:
        return '不带停止激活的节传输'
    elif LSQ == 4:
        return '带停止激活的节传输'
    elif 5 <= LSQ <= 127:
        return '标准最后节段限定词%s' % LSQ
    elif 128 <= LSQ <= 255:
        return '特定最后节段限定词%s' % LSQ


# 7.2.6.32
def unpack_AFQ(data: int):
    """解析 文件认可或节认可限定词"""
    Word = data & 0b1111
    Err = (data & 0b11110000) >> 4
    if Word == 0:
        Word = '缺省'
    elif Word == 1:
        Word = '文件传输的肯定认可'
    elif Word == 2:
        Word = '文件传输的否定认可'
    elif Word == 3:
        Word = '节传输的肯定认可'
    elif Word == 4:
        Word = '节传输的否定认可'
    elif 5 <= Word <= 10:
        Word = '标准限定词%s' % Word
    elif 11 <= Word <= 15:
        Word = '特定限定词%s' % Word
    
    if Err == 0:
        Err = '缺省'
    elif Err == 1:
        Err = '无所请求的存储空间'
    elif Err == 2:
        Err = '校验和错'
    elif Err == 3:
        Err = '非所期望的通信服务'
    elif Err == 4:
        Err = '非所期望的文件名称'
    elif Err == 5:
        Err = '非所期望的节名称'
    elif 6 <= Err <= 10:
        Err = '标准错误%s' % Err
    elif 11 <= Err <= 15:
        Err = '特定错误%s' % Err
    return {'限定词': Word, '错误信息': Err}


# 7.2.6.33
def unpack_NOF(data: int):
    """解析 文件名称"""
    return data if data else '缺省'


# 7.2.6.34
def unpack_NOS(data: int):
    """解析 节名称"""
    return data if data else '缺省'


# 7.2.6.35
def unpack_LOF(data: bytes):
    """解析 文件或节的长度"""
    return unpack('<I', data)[0]


# 7.2.6.36
def unpack_LOS(data: int):
    """解析 段的长度"""
    return data


# 7.2.6.37
def unpack_CHS(data: int):
    """解析 校验和"""
    return data


# 7.2.6.38
def unpack_SOF(data: int):
    """解析 文件状态"""
    STATUS = data & 0b11111
    LFD = data & 0b100000
    FOR = data & 0b1000000
    FA = data & 0b10000000
    if STATUS == 0:
        STATUS = '缺省'
    elif 1 <= STATUS <= 15:
        STATUS = '标准文件状态%s' % STATUS
    elif 16 <= STATUS <= 31:
        STATUS = '特定文件状态%s' % STATUS
    return {
        '文件状态': STATUS, 
        '是否最后目录文件': '最后目录文件' if LFD else '后面还有目录文件', 
        '定义名称': '定义子目录名' if FOR else '定义文件名', 
        '文件传输是否已激活': '文件传输已激活' if FA else '文件等待传输', 
    }


# 7.2.6.39
def unpack_QOS(data: int):
    """解析 设定命令限定词"""
    QL = data & 0b1111111
    if QL == 0:
        QL = '缺省'
    elif 1 <= QL <= 63:
        QL = '标准设定命令限定词%s' % QL
    elif 64 <= QL <= 127:
        QL = '特定设定命令限定词%s' % QL
    return {
        '设定命令限定词': QL, 
        'S/E': '选择' if data & 0b10000000 else '执行'
    }


# 7.2.6.40
def unpack_SCD(data: bytes):
    """解析 状态和状态变位检出"""
    return  {
        '开(0)/合(1)': bin(data[1]).strip('0b') + bin(data[0]).strip('0b'), 
        '上次报告后未检出(0)/至少检出一次(1)到的状态变化': bin(data[3]).strip('0b') + bin(data[2]).strip('0b'), 
    }


################################ 基于类型标识的应用数据单元解析 ################################
def unpack_info_elems(type_id: int, data: bytes):
    """解析一个类型标识为type_id的信息元素集"""
    ############## 在监视方向过程信息的应用服务数据单元 ##############
    if type_id == M_SP_NA_1:
        # 7.3.1.1 单点信息
        return unpack_SIQ(data[0])

    elif type_id == M__SP__TA__1:
        # 7.3.1.2 带时标的单点信息
        return unpack_SIQ(data[0]), unpack_CP24Time2a(data[1:4])

    elif type_id == M__DP__NA__1:
        # 7.3.1.3 不带时标的双点信息
        return unpack_DIQ(data[0])

    elif type_id == M__DP__TA__1:
        # # 7.3.1.4 带时标的双点信息
        return unpack_DIQ(data[0]), unpack_CP24Time2a(data[1:4])

    elif type_id == M__ST__NA__1:
        # 7.3.1.5 不带时标的步位置信息
        return unpack_VTI(data[0]), unpack_QDS(data[1])

    elif type_id == M__ST__TA__1:
        # 7.3.1.6 带时标的步位置信息
        return unpack_VTI(data[0]), unpack_QDS(data[1]), unpack_CP24Time2a(data[2:5])

    elif type_id == M__BO__NA__1:
        # 7.3.1.7 32比特串
        return unpack_BSI(data[0:4]), unpack_QDS(data[4])
    
    elif type_id == M__BO__TA__1:
        # 7.3.1.8 带时标的32比特串
        return unpack_BSI(data[0:4]), unpack_QDS(data[4]), unpack_CP24Time2a(data[5:8])
    
    elif type_id == M__ME__NA__1:
        # 7.3.1.9 测量值，规一化值
        return unpack_NVA(data[0:2]), unpack_QDS(data[2])
    
    elif type_id == M__ME__TA__1:
        # 7.3.1.10 测量值，带时标的规一化值
        return unpack_NVA(data[0:2]), unpack_QDS(data[2]), unpack_CP24Time2a(data[3:6])
    
    elif type_id == M__ME__NB__1:
        # 7.3.1.11 测量值，标度化值
        return unpack_SVA(data[0:2]), unpack_QDS(data[2])
    
    elif type_id == M__ME__TB__1:
        # 7.3.1.12 测量值，带时标的标度化值
        return unpack_SVA(data[0:2]), unpack_QDS(data[2]), unpack_CP24Time2a(data[3:6])

    elif type_id == M__ME__NC__1:
        # 7.3.1.13 测量值，短浮点数
        return unpack_float32(data[:4]), unpack_QDS(data[4])
    
    elif type_id == M__ME__TC__1:
        # 7.3.1.14 测量值，带时标短浮点数
        return unpack_float32(data[:4]), unpack_QDS(data[4]), unpack_CP24Time2a(data[5:8])
    
    elif type_id == M__IT__NA__1:
        # 7.3.1.15 累计量
        return unpack_BCR(data[:5])
    
    elif type_id == M__IT__TA__1:
        # 7.3.1.16 带时标的累计量
        return unpack_BCR(data[:5]), unpack_CP24Time2a(data[5:8])
    
    elif type_id == M__EP__TA__1:
        # 7.3.1.17 带时标的继电保护设备事件
        return unpack_SEP(data[0]), unpack_CP16Time2a(data[1:3]), unpack_CP24Time2a(data[3:6])
    
    elif type_id == M__EP__TB__1:
        # 7.3.1.18 带时标的继电保护设备成组启动事件
        return unpack_SPE(data[0]), unpack_QDP(data[1]), unpack_CP16Time2a(data[2:4]), unpack_CP24Time2a(data[4:7])
    
    elif type_id == M__EP__TC__1:
        # 7.3.1.19 带时标的继电保护设备成组输出电路信息
        return unpack_OCI(data[0]), unpack_QDP(data[1]), unpack_CP16Time2a(data[2:4]), unpack_CP24Time2a(data[4:7])
    
    elif type_id == M__PS__NA__1:
        # 7.3.1.20 带变位检出的成组单点信息
        return unpack_SCD(data[0:4]), unpack_QDS(data[4])
    
    elif type_id == M__ME__ND__1:
        # 7.3.1.21 测量值，不带品质描述词的规一化值
        return unpack_NVA(data[0:2])
    
    elif type_id == M__SP__TB__1:
        # 7.3.1.22 带时标CP56Time2a的单点信息
        return unpack_SIQ(data[0]), unpack_CP56Time2a(data[1:8])
    
    elif type_id == M__DP__TB__1:
        # 7.3.1.23 带时标CP56Time2a的双点信息
        return unpack_DIQ(data[0]), unpack_CP56Time2a(data[1:8])
    
    elif type_id == M__ST__TB__1:
        # 7.3.1.24 带时标的步位置信息
        return unpack_VTI(data[0]), unpack_QDS(data[1]), unpack_CP56Time2a(data[2:9])
    
    elif type_id == M__BO__TB__1:
        # 7.3.1.25 带时标CP56Time2a的32比特串
        return unpack_BSI(data[0:4]), unpack_QDS(data[4]), unpack_CP56Time2a(data[5:12])
    
    elif type_id == M__ME__TD__1:
        # 7.3.1.26 测量值，带时标CP56Time2a的规一化值
        return unpack_NVA(data[0:2]), unpack_QDS(data[2]), unpack_CP56Time2a(data[3:10])
    
    elif type_id == M__ME__TE__1:
        # 7.3.1.27 测量值，带时标CP56Time2a的标度化值
        return unpack_SVA(data[0:2]), unpack_QDS(data[2]), unpack_CP56Time2a(data[3:10])
    
    elif type_id == M__ME__TF__1:
        # 7.3.1.28 测量值，带时标CP56Time2a的短浮点数
        return unpack_float32(data[0:4]), unpack_QDS(data[4]), unpack_CP56Time2a(data[5:12])
    
    elif type_id == M__IT__TB__1:
        # 7.3.1.29 带时标CP56Time2a的累计量
        return unpack_BCR(data[0:5]), unpack_CP56Time2a(data[5:12])
    
    elif type_id == M__EP__TD__1:
        # 7.3.1.30 带时标CP56Time2a的继电保护设备事件
        return unpack_SEP(data[0]), unpack_CP16Time2a(data[1:3]), unpack_CP56Time2a(data[3:10])
    
    elif type_id == M__EP__TE__1:
        # 7.3.1.31 带时标CP56Time2a的继电保护设备成组启动事件
        return unpack_SPE(data[0]), unpack_QDP(data[1]), unpack_CP16Time2a(data[2:4]), unpack_CP56Time2a(data[4:11])
    
    elif type_id == M__EP__TF__1:
        # 7.3.1.32 带时标CP56Time2a的继电保护设备成组输出电路信息
        return unpack_OCI(data[0]), unpack_QDP(data[1]), unpack_CP16Time2a(data[2:4]), unpack_CP56Time2a(data[4:11])
    
    ############## 在控制方向过程信息的应用服务数据单元 ##############
    elif type_id == C__SC__NA__1:
        # 7.3.2.1 单命令
        return unpack_SCO(data[0])

    elif type_id == C__DC__NA__1:
        # 7.3.2.2 双命令
        return unpack_DCO(data[0])
    
    elif type_id == C__RC__NA__1:
        # 7.3.2.3 步调节命令
        return unpack_RCO(data[0])
    
    elif type_id == C__SE__NA__1:
        # 7.3.2.4 设定命令，规一化值
        return unpack_NVA(data[0:2]), unpack_QOS(data[2])
    
    elif type_id == C__SE__NB__1:
        # 7.3.2.5 设定命令，标度化值
        return unpack_SVA(data[0:2]), unpack_QOS(data[2])
    
    elif type_id == C__SE__NC__1:
        # 7.3.2.6 设定命令，短浮点数
        return unpack_float32(data[0:4]), unpack_QOS(data[4])
    
    elif type_id == C__BO__NA__1:
        # 7.3.2.7 32比特串
        return unpack_BSI(data[0:4])

    ############## 在控制方向过程信息的应用服务数据单元 ##############
    elif type_id == M__EI__NA__1:
        # 7.3.3 初始化结束
        return unpack_COI(data[0])

    ############## 在控制方向系统信息的应用服务数据单元 ##############
    elif type_id == C__IC__NA__1:
        # 7.3.4.1 召唤命令
        return unpack_QOI(data[0])
    
    elif type_id == C__CI__NA__1:
        # 7.3.4.2 计数量召唤命令
        return unpack_QCC(data[0])
    
    elif type_id == C_RD_NA_1:
        # 7.3.4.3 读命令
        return
    
    elif type_id == C_CS_NA_1:
        # 7.3.4.4 时钟同步命令
        return unpack_CP56Time2a(data[0:7])

    elif type_id == C_TS_NA_1:
        # 7.3.4.5 测试命令
        return unpack_FBP(data[0:2])
    
    elif type_id == C_RP_NA_1:
        # 7.3.4.6 复位进程命令
        return unpack_QRP(data[0])
    
    elif type_id == C_CD_NA_1:
        # 7.3.4.7 延时获得命令
        return unpack_CP16Time2a(data[0:2])
    
    ############## 在控制方向参数的应用服务数据单元 ##############
    elif type_id == P_ME_NA_1:
        # 7.3.5.1 测量值参数，规一化值
        return unpack_NVA(data[0:2]), unpack_QPM(data[2])

    elif type_id == P_ME_NB_1:
        # 7.3.5.2 测试值参数，标度化值
        return unpack_SVA(data[0:2]), unpack_QPM(data[2])

    elif type_id == P_ME_NC_1:
        # 7.3.5.3 测量值参数，短浮点数
        return unpack_float32(data[0:4]), unpack_QPM(data[4])
    
    elif type_id == P_AC_NA_1:
        # 7.3.5.4 参数激活
        return unpack_QPA(data[0])

    elif type_id == F_FR_NA_1:
        # 7.3.6.1 文件准备就绪
        return unpack_NOF(data[0]), unpack_LOF(data[1]), unpack_FRQ(data[2])

    elif type_id == F_SR_NA_1:
        # 7.3.6.2 节准备就绪
        return unpack_NOF(data[0]), unpack_NOS(data[1]), unpack_LOS(data[2]), unpack_SRQ(data[3])

    elif type_id == F_SC_NA_1:
        # 7.3.6.3 召唤目录，选择文件，召唤文件，召唤节
        return unpack_NOF(data[0]), unpack_NOS(data[1]), unpack_SCQ(data[2])
    
    elif type_id == F_LS_NA_1:
        # 7.3.6.4 最后的节，最后的段
        return unpack_NOF(data[0]), unpack_NOS(data[1]), unpack_LSQ(data[2]), unpack_CHS(data[3])

    elif type_id == F_AF_NA_1:
        # 7.3.6.5 认可文件，认可节
        return unpack_NOF(data[0]), unpack_NOS(data[1]), unpack_AFQ(data[2])

    elif type_id == F_SG_NA_1:
        # 7.3.6.6 段
        return unpack_NOF(data[0]), unpack_NOS(data[1]), unpack_LOS(data[2]), data[3:]

    elif type_id == F_DR_TA_1:
        # 7.3.6.7 目录
        return unpack_NOF(data[0]), unpack_LOF(data[1]), unpack_SOF(data[2]), unpack_CP56Time2a(data[3:10])


################################ 结构解析 ################################
def unpack_info_obj_set(type_id: int, info_objs_total_number: int, data: bytes) -> list:
    """解析信息对象集合：
        信息对象地址1 信息元素集1
        ......
        信息对象地址1 信息元素集n
    """
    info_objs = []
    info_obj_size = int(len(data) / info_objs_total_number)

    for i in range(0, len(data), info_obj_size):
        info_objs.append({
            'addr': unpack_info_obj_addr(data[i:INFO_ADDR_SIZE]), 
            'elems': unpack_info_elems(type_id, data[i+INFO_ADDR_SIZE:i+info_obj_size]), 
        })

    return info_objs


def unpack_info_obj_sq(type_id: int, info_objs_total_number: int, data: bytes) -> list:
    """解析信息对象序列：
        信息对象地址（基地址）
        信息元素集1
        ......
        信息元素集n
    """
    info_objs, counter = [], 0
    info_obj_addr_base = unpack_info_obj_addr(data[:INFO_ADDR_SIZE])
    elem_size = int((len(data) - INFO_ADDR_SIZE) / info_objs_total_number)
    for i in range(INFO_ADDR_SIZE, len(data), elem_size):
        info_objs.append({
            'addr': info_obj_addr_base + counter, 
            'elems': unpack_info_elems(type_id, data[i:i+elem_size]), 
        })
        counter += 1
    return info_objs


def unpack_asdu(data: bytes):
    """解析数据单元标识符"""
    # 类型标识，定义了信息对象的结构和类型
    type_id = data[0]

    # 可变结构限定词，描述了信息对象的个数，信息对象是否为一个序列（即同一个信息对像类型的数组）
    vsq = {
        'info_objs_total_number': data[1] & 0b1111111, 
        'is_sq': (data[1] & 0b10000000) >> 7
    }

    # 传送原因：原因, P/N, T, (源发者地址，根据系统参数设置决定是否包含该字段)
    trans_cause = {
        'cause': TRANS_CAUSE_DESC.get(data[2] & 0b111111, ''),   # 第三个字节前六位表传送原因
        'P/N': (data[2] & 0b1000000) >> 6,  # 第三个字节第七位表肯定确认或否定确认(P/N)
        'T': (data[2] & 0b10000000) >> 7,  # 第三个字节第八位表实验/未实验(T)
    }
    if TRANS_CAUSE_SIZE == 2:
        trans_cause['source_addr'] = data[3]  # 第四个字节若被传送原因采用，则表源发者地址

    # 公共地址：一或两个字节（根据系统参数决定）
    common_addr_bytes = data[2 + TRANS_CAUSE_SIZE:2 + TRANS_CAUSE_SIZE + COMMON_ADDR_SIZE]
    common_addr = unpack('<H', common_addr_bytes)[0]

    # 信息对象：分为集合和序列两种结构
    info_objs_bytes = data[2 + TRANS_CAUSE_SIZE + COMMON_ADDR_SIZE:]
    if vsq['is_sq'] == True:
        info_objs = unpack_info_obj_sq(type_id, vsq['info_objs_total_number'], info_objs_bytes)
    else:
        info_objs = unpack_info_obj_set(type_id, vsq['info_objs_total_number'], info_objs_bytes)

    return ASDU(type_id, vsq, trans_cause, common_addr, info_objs)


def unpack_apci(data: bytes) -> tuple:
    """解析apci数据
    APCI为应用协议控制信息, 表征着报文的作用, 不承载传输数据
    第一个字节为0x68, 为IEC104报文的起始标志位, 标志着报文的开始
    第二个字节表示了IEC104报文的长度, 即从第三个字节到结束共有多少字节
    """
    pdu_send, pdu_recv = 0, 0
    if data[2] & 0b1 == 0b0:
        '''第三个字节的第一位为0则该报文为I格式
        对于I格式的报文, 有APCI和ASDU两个部分, ASDU承载了待传输的数据'''
        pdu_format = 'I'
        pdu_action = 'TRANSMIT'
        pdu_send = unpack('<H', data[2:4])[0]
        pdu_recv = unpack('<H', data[4:6])[0]
    elif data[2] & 0b11 == 0b01:
        '''第三个字节的第一位和第二位为01则表示该报文为S格式
        S格式的报文仅用于监视而不传输数据'''
        pdu_format = 'S'
        pdu_action = 'MONITOR'
        pdu_recv = unpack('<H', data[4:6])[0]
    else:
        '''第三个字节的第一位和第二位为11则表示该报文为U格式
        U格式报文可看成一句指令, 此处第三个字节的第一位和第二位必为11, 逻辑判断省略'''
        pdu_format = 'U'
        pdu_action = U_ACTIONS[int(log2((data[2]-0b11)>>2))]  # 解析指令详情

    return pdu_format, pdu_action, pdu_send, pdu_recv


def unpack_apdu(data: bytes) -> APDU:
    pdu_format, pdu_action, pdu_send, pdu_recv = unpack_apci(data[:APCI_SIZE])
    # 仅当apci格式为I格式时有asdu信息
    if pdu_format == 'I':
        return APDU(pdu_format, pdu_action, pdu_send, pdu_recv, unpack_asdu(data[APCI_SIZE:]))
    else:
        return APDU(pdu_format, pdu_action, pdu_send, pdu_recv,)


def from_bytes_to_apdus(data: bytes) -> list:
    if not data:
        return []

    if data[0] == 0x68:
        pack_size = data[1] + 2
        return [unpack_apdu(data[:pack_size]), ] + from_bytes_to_apdus(data[pack_size:])
