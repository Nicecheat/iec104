# 本模块定义了传输协议集各层次的控制和结构信息(header information)
# 参考协议：`IEC 60870-5-104`

from struct import unpack
from math import log2
from data import *
from iec_types import *
from unpack_101 import unpack_asdu


def unpack_apci(data: bytes) -> APCI:
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
        pdu_action = U_ACTIONS[int(log2(data[2]-0b11))]  # 解析指令详情

    return APCI(format=pdu_format, action=pdu_action, send=pdu_send, recv=pdu_recv)


def unpack_apdu(data: bytes) -> APDU:
    apci = unpack_apci(data[:APCI_SIZE])
    # 仅当apci格式为I格式时有asdu信息
    if apci.format == 'I':
        return APDU(apci=apci, asdu=unpack_asdu(data[APCI_SIZE:]), data=data)
    else:
        return APDU(apci=apci, asdu=None, data=data)


def unpack_apdus(data: bytes) -> list:
    if not data:
        return []

    if data[0] == 0x68:
        pack_size = data[1]+2
        return [unpack_apdu(data[:pack_size]), ] + unpack_apdus(data[pack_size:])
