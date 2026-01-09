import socket
import threading
import time

class DHZBOX:
    def __init__(self, IP, PORT, RANDOM):
        self.IP = IP
        self.PORT = PORT
        self.RANDOM = RANDOM
        self.LEFTSTATE = 0
        self.RIGHTSTATE = 0
        self.MIDDLESTATE = 0
        self.SIDE1STATE = 0
        self.SIDE2STATE = 0
        self.RECEIVER_FLAG = False

    def __encrypt_string(self, str):
        key = self.RANDOM
        encrypted_string = []
        for char in str:
            if char.isalpha():
                if char.islower():
                    new_char = chr((ord(char) - ord('a') + key) % 26 + ord('a'))
                else:  # inserted
                    if char.isupper():
                        new_char = chr((ord(char) - ord('A') + key) % 26 + ord('A'))
                encrypted_string.append(new_char)
            else:  # inserted
                encrypted_string.append(char)
        return ''.join(encrypted_string)

    def __udp_sender(self, message):
        SCOK_sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            SCOK_sender.settimeout(1)
            SCOK_sender.sendto(message.encode(), (self.IP, self.PORT))
            try:
                reply, _ = SCOK_sender.recvfrom(1024)
            except socket.timeout:
                print('接收超时，未收到回复')
        finally:  # inserted
            SCOK_sender.close()

    def __udp_receiver(self, port, ip=''):
        print(port)
        SCOK_receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        SCOK_receiver.bind((ip, port))
        while self.RECEIVER_FLAG:
            data, address = SCOK_receiver.recvfrom(1024)
            mag = data.decode()
            try:
                cmd = mag.split('|')
                self.LEFTSTATE = int(cmd[0])
                self.MIDDLESTATE = int(cmd[1])
                self.RIGHTSTATE = int(cmd[2])
                self.SIDE1STATE = int(cmd[3])
                self.SIDE2STATE = int(cmd[4])
            except:
                self.LEFTSTATE, self.RIGHTSTATE, self.MIDDLESTATE, self.SIDE1STATE, self.SIDE2STATE = (0, 0, 0, 0, 0)
        print(port, '监听线程已关闭')
        SCOK_receiver.close()

    def __udp_receiver2(self, port, ip=''):
        print(port)
        SCOK_receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        SCOK_receiver.bind((ip, port))
        while self.RECEIVER_FLAG:
            data, address = SCOK_receiver.recvfrom(1024)
            mag = data.decode()
        print(port, '监听线程已关闭')
        SCOK_receiver.close()
    pass
    def move(self, x, y):
        cmd = self.__encrypt_string(f'move({int(x)},{int(y)})')
        self.__udp_sender(cmd)

    def left(self, state):
        cmd = self.__encrypt_string(f'left({int(state)})')
        self.__udp_sender(cmd)

    def right(self, state):
        cmd = self.__encrypt_string(f'right({int(state)})')
        self.__udp_sender(cmd)

    def middle(self, state):
        cmd = self.__encrypt_string(f'middle({int(state)})')
        self.__udp_sender(cmd)

    def wheel(self, state):
        cmd = self.__encrypt_string(f'wheel({int(state)})')
        self.__udp_sender(cmd)

    def mouse(self, button, x, y, w):
        cmd = self.__encrypt_string(f'mouse({int(button)},{int(x)},{int(y)},{int(w)})')
        self.__udp_sender(cmd)

    def side1(self, state):
        cmd = self.__encrypt_string(f'side1({int(state)})')
        self.__udp_sender(cmd)

    def side2(self, state):
        cmd = self.__encrypt_string(f'side2({int(state)})')
        self.__udp_sender(cmd)
    pass
    def monitor(self, port):
        if port == 0:
            cmd = self.__encrypt_string('monitor(0)')
            self.RECEIVER_FLAG = False
            self.__udp_sender(cmd)
            time.sleep(0.5)
        else:  # inserted
            if abs(port) > 0:
                cmd = self.__encrypt_string(f'monitor({int(port)})')
                self.__udp_sender(cmd)
                self.RECEIVER_FLAG = True
                t_receiver = threading.Thread(target=self.__udp_receiver, name='t_receiver', args=(port,))
                t_receiver.daemon = True
                t_receiver.start()

    def isdown_left(self):
        return self.LEFTSTATE

    def isdown_middle(self):
        return self.MIDDLESTATE

    def isdown_right(self):
        return self.RIGHTSTATE

    def isdown_side1(self):
        return self.SIDE2STATE

    def isdown_side2(self):
        return self.SIDE1STATE
    pass
    def mask_left(self, state):
        cmd = self.__encrypt_string(f'mask_left({int(state)})')
        self.__udp_sender(cmd)

    def mask_right(self, state):
        cmd = self.__encrypt_string(f'mask_right({int(state)})')
        self.__udp_sender(cmd)

    def mask_middle(self, state):
        cmd = self.__encrypt_string(f'mask_middle({int(state)})')
        self.__udp_sender(cmd)

    def mask_wheel(self, state):
        cmd = self.__encrypt_string(f'mask_wheel({int(state)})')
        self.__udp_sender(cmd)

    def mask_side1(self, state):
        cmd = self.__encrypt_string(f'mask_side1({int(state)})')
        self.__udp_sender(cmd)

    def mask_side2(self, state):
        cmd = self.__encrypt_string(f'mask_side2({int(state)})')
        self.__udp_sender(cmd)

    def mask_x(self, state):
        cmd = self.__encrypt_string(f'mask_x({int(state)})')
        self.__udp_sender(cmd)

    def mask_y(self, state):
        cmd = self.__encrypt_string(f'mask_y({int(state)})')
        self.__udp_sender(cmd)

    def mask_all(self, state):
        cmd = self.__encrypt_string(f'mask_all({int(state)})')
        self.__udp_sender(cmd)