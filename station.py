import time
import socket
from struct import pack

from iec_types import *
from unpack import from_bytes_to_apdus


RECV_SIZE = 1024*12


class BaseStation:
    def __init__(self, ip: str, port: int) -> None:
        # 站状态信息初始化
        # 计数器
        self.ack = 0
        self.vs = 0
        self.vr = 0
        # 站连接初始化
        self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_sock.connect((ip, port))


    def recv(self) -> list:
        """接收数据包"""
        # 从缓存区读入比特流
        data = self.tcp_sock.recv(RECV_SIZE)
        # 解析比特流为apdu列表
        apdus = from_bytes_to_apdus(data)
        # 更新站状态信息
        for apdu in apdus:
            assert isinstance(apdu, APDU)
            if apdu.format == 'I':
                if apdu.recv != self.vs or apdu.send != self.vr:
                    print('顺序错误！主动关闭')
                    self.tcp_sock.close() # 主动关闭
                else:
                    print('接收成功！')
                    print(apdu)
                    self.ack = apdu.recv
                    self.vr += 1

            elif apdu.format == 'S':
                if apdu.recv != self.vs:
                    print('顺序错误!')
                    self.tcp_sock.close() # 主动关闭
                else:
                    print('接收成功')
                    self.ack = apdu.recv
                    self.vr += 1

        return apdus


    def send(self, frame_format: str, frame_action: str = '', asdu_bytes: bytes = b'') -> None:
        """发送数据包"""
        # data中添加bytes格式的apdu报文
        length = pack('B', len(asdu_bytes) + 4)
        if frame_format == 'I':
            control_bytes = pack('<H', self.vs << 1)  + pack('<H', self.vr << 1)
            self.vs += 1

        elif frame_format == 'S':
            control_bytes = pack('<H', 1) + pack('<H', self.vr << 1)
            self.vs += 1

        elif frame_format == 'U':
            control_bytes = pack('<H', ((2**U_ACTIONS.index(frame_action))<<2)+0b11) + b'\x00\x00'

        data = b'h%s%s%s' % (length, control_bytes, asdu_bytes)
        # 发送数据
        print('发送：', from_bytes_to_apdus(data)[0])
        self.tcp_sock.send(data)


class ControlStation(BaseStation):
    """控制站，又称主站
    
    对于每一个基本应用功能，主站和从站具有不同的行为，分别定义如下：
    """
    def init(self):
        """站初始化"""
        pass


    def query_data(self):
        """用查询方式采集数据"""
        pass


    def cyclic_transmit(self):
        """循环数据传输"""
        pass


    def collect_event(self):
        """事件收集"""
        pass


    def total_call(self):
        """总召唤"""
        print(f'self.vs  = {self.vs}, self.vr = {self.vr}')
        self.send('U', 'STARTDT ACTIVATE')
        time.sleep(1)
        self.recv()
        self.send('I', asdu_bytes=bytes.fromhex('64010600010000000014'))
        time.sleep(1)
        self.recv()
        return


    def synchronize_clock(self):
        """时钟同步"""
        pass


    def transmit_cmd(self):
        """命令传输"""
        pass


    def transmit_cumulative_amount(self):
        """累计量传输"""
        pass


    def load_parameters(self):
        """装载参数"""
        pass


    def test(self):
        """测试"""
        pass


    def transmit_file(self):
        """文件传输"""
        pass


    def collect_transmission_delay(self):
        """传输延时采集"""
        pass


class ControledStation(BaseStation):
    """被控站，又称从站
    
    对于每一个基本应用功能，主站和从站具有不同的行为，分别定义如下：
    """
    def init(self):
        """站初始化"""
        pass  # TODO: 暂未实现


    def query_data(self):
        """用查询方式采集数据"""
        pass


    def cyclic_transmit(self):
        """循环数据传输"""
        pass


    def collect_event(self):
        """事件收集"""
        pass


    def total_call(self):
        """总召唤"""
        pass


    def synchronize_clock(self):
        """时钟同步"""
        pass


    def transmit_cmd(self):
        """命令传输"""
        pass


    def transmit_cumulative_amount(self):
        """累计量传输"""
        pass


    def load_parameters(self):
        """装载参数"""
        pass


    def test(self):
        """测试"""
        pass


    def transmit_file(self):
        """文件传输"""
        pass


    def collect_transmission_delay(self):
        """传输延时采集"""
        pass
