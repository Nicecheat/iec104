# 本模块定义了远动设备系统传输协议集各个层次数据的一般抽象
from data import *


class ASDU:
    """Application Service Data Unit"""
    def __init__(self, type_id: int, vsq: dict, trans_cause: dict, common_addr: int, info_objs: list) -> None:
        self.type_id = type_id  # Type identification
        self.vsq = vsq  # Variable Structure Qualifier
        self.trans_cause = trans_cause  # Cause of Transmission
        self.common_addr = common_addr  # Common address
        self.info_objs = info_objs  # Information objects


class APDU:
    """Application Protocol Data Unit"""
    def __init__(self, format: str, action: str, send: int = 0, recv: int = 0, asdu: ASDU or None = None) -> None:
        assert format in ('I', 'S', 'U')
        assert action in (U_ACTIONS + ('TRANSMIT', 'MONITOR'))
        assert send > -1
        assert recv > -1
        self.format = format
        self.action = action
        self.send = send
        self.recv = recv
        self.asdu = asdu


    def __str__(self) -> str:
        if self.format == 'I':
            if self.asdu.info_objs:
                return 'I(%s, %s): \nTYPE: %s\nVSQ : %s\nCOT : %s\nOBJS: %s\n' % (
                    self.send, 
                    self.recv, 
                    TYPE_DESC[self.asdu.type_id], 
                    self.asdu.vsq, 
                    self.asdu.trans_cause, 
                    self.asdu.info_objs)
            else:
                return 'I(%s, %s)' % (self.send, self.recv)
        elif self.format == 'S':
            return 'S(%s)' % self.recv
        elif self.format == 'U':
            return 'U(%s)' % self.action

