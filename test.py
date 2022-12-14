def test_from_bytes_to_apdus():
    msg1 = b'h\x04\x0b\x00\x00\x00'
    msg2 = b'h\x0e\x00\x00\x00\x00F\x01\x04\x00\x01\x00\x00\x00\x00\x00'
    msg3 = b'h\xfd\x06\x00\x02\x00\r\xb0\x14\x00\x01\x00\x01@\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\x00\x00\x00\x00\x80\x00\x00\x00\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xcd\xcc\xb0B\x00\x00\x00\xb5B\x0033\xafB\x00\xcd\xccL@\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xc2\xf5\xe8?\x00\x99\x99\xb9?\x00'
    msg4 = b'h\x0e\x14\x00\x02\x00d\x01\n\x00\x01\x00\x00\x00\x00\x14'
    msg5 = b'h\x0e\x02\x00\x02\x00d\x01\x07\x00\x01\x00\x00\x00\x00\x14'
    msg6 = b'h\x04\x07\x00\x00\x00'
    msg = b''.join([msg1, msg2, msg3, msg4, msg5, msg6, ])
    from unpack import from_bytes_to_apdus
    for packet in from_bytes_to_apdus(msg):
        print(packet)


def test_station():
    from station import ControlStation
    s = ControlStation(ip='192.168.0.42', port=2404)
    s.total_call()


if __name__ == '__main__':
    # test_from_bytes_to_apdus()
    test_station()
