import socket
import threading
import struct
import logging
from logging.handlers import RotatingFileHandler
import time
import traceback
from typing import Dict, Any, List, Tuple, Optional


# 配置日志系统
def setup_logging():
    # 创建主日志器
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 创建文件处理器，支持日志轮转
    file_handler = RotatingFileHandler(
        'logs/fastmcp_proxy.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)

    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 为处理器设置格式化器
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # 为日志器添加处理器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # 创建各组件的日志器
    return {
        'main': logging.getLogger('main'),
        'client': logging.getLogger('client'),
        'server': logging.getLogger('server'),
        'protocol': logging.getLogger('protocol'),
        'handler': logging.getLogger('handler')
    }


class FastMCPPacket:
    """FastMCP数据包处理类"""

    def __init__(self, loggers):
        self.logger = loggers['protocol']

    def read_header(self, sock: socket.socket) -> Tuple[int, int, int]:
        """读取数据包头部 (协议版本, 数据包类型, 数据长度)"""
        try:
            start_time = time.time()
            header = sock.recv(8)
            read_time = (time.time() - start_time) * 1000  # 毫秒

            if len(header) < 8:
                raise EOFError("连接已关闭")

            version, packet_type, length = struct.unpack('>HHI', header)
            self.logger.debug(
                f"读取头部: 版本={version}, 类型=0x{packet_type:04X}, 长度={length}, 耗时={read_time:.2f}ms")
            return version, packet_type, length
        except Exception as e:
            self.logger.error(f"读取头部失败: {e}")
            raise

    def write_header(self, version: int, packet_type: int, length: int) -> bytes:
        """写入数据包头部"""
        try:
            header = struct.pack('>HHI', version, packet_type, length)
            self.logger.debug(f"写入头部: 版本={version}, 类型=0x{packet_type:04X}, 长度={length}")
            return header
        except Exception as e:
            self.logger.error(f"写入头部失败: {e}")
            raise

    def read_data(self, sock: socket.socket, length: int) -> bytes:
        """读取数据包数据部分"""
        try:
            start_time = time.time()
            data = bytearray()
            while len(data) < length:
                chunk = sock.recv(length - len(data))
                if not chunk:
                    raise EOFError("连接已关闭")
                data.extend(chunk)
            read_time = (time.time() - start_time) * 1000  # 毫秒

            self.logger.debug(f"读取数据: 长度={length}, 耗时={read_time:.2f}ms")
            return bytes(data)
        except Exception as e:
            self.logger.error(f"读取数据失败: 长度={length}, 错误={e}")
            raise

    def read_packet(self, sock: socket.socket) -> Tuple[int, int, bytes]:
        """读取完整数据包"""
        try:
            version, packet_type, length = self.read_header(sock)
            data = self.read_data(sock, length)
            self.logger.info(f"读取完整数据包: 类型=0x{packet_type:04X}, 长度={length}")
            return version, packet_type, data
        except Exception as e:
            self.logger.error(f"读取数据包失败: {e}")
            raise

    def write_packet(self, sock: socket.socket, version: int, packet_type: int, data: bytes) -> None:
        """写入完整数据包"""
        try:
            start_time = time.time()
            header = self.write_header(version, packet_type, len(data))
            sock.sendall(header + data)
            write_time = (time.time() - start_time) * 1000  # 毫秒

            self.logger.info(f"写入数据包: 类型=0x{packet_type:04X}, 长度={len(data)}, 耗时={write_time:.2f}ms")
        except Exception as e:
            self.logger.error(f"写入数据包失败: 类型=0x{packet_type:04X}, 错误={e}")
            raise


class MCPFastClient:
    """MCP客户端连接到FastMCP服务"""

    def __init__(self, host: str, port: int, loggers):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.packet_processor = FastMCPPacket(loggers)
        self.logger = loggers['client']
        self.request_id = 0

    def connect(self) -> None:
        """连接到FastMCP服务"""
        try:
            self.logger.info(f"尝试连接到FastMCP服务: {self.host}:{self.port}")
            start_time = time.time()

            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)  # 设置连接超时时间
            self.socket.connect((self.host, self.port))

            connect_time = (time.time() - start_time) * 1000  # 毫秒
            self.connected = True
            self.logger.info(f"成功连接到FastMCP服务, 耗时={connect_time:.2f}ms")
        except Exception as e:
            self.logger.error(f"连接失败: {e}")
            self.connected = False
            raise

    def disconnect(self) -> None:
        """断开与FastMCP服务的连接"""
        try:
            if self.socket:
                self.logger.info("断开与FastMCP服务的连接")
                self.socket.close()
                self.connected = False
        except Exception as e:
            self.logger.error(f"断开连接失败: {e}")

    def send_request(self, packet_type: int, data: bytes) -> Tuple[int, bytes]:
        """发送请求并接收响应"""
        if not self.connected:
            self.logger.error("未连接到FastMCP服务")
            raise Exception("未连接到FastMCP服务")

        try:
            # 增加请求ID
            self.request_id += 1

            # 记录请求开始
            self.logger.info(f"发送请求 #{self.request_id}: 类型=0x{packet_type:04X}, 长度={len(data)}")
            self.logger.debug(f"请求 #{self.request_id} 数据: {data.hex()}")

            # 发送请求
            start_time = time.time()
            self.packet_processor.write_packet(self.socket, 1, packet_type, data)
            send_time = (time.time() - start_time) * 1000  # 毫秒
            self.logger.debug(f"请求 #{self.request_id} 发送完成, 耗时={send_time:.2f}ms")

            # 接收响应
            start_time = time.time()
            version, response_type, response_data = self.packet_processor.read_packet(self.socket)
            receive_time = (time.time() - start_time) * 1000  # 毫秒

            self.logger.info(
                f"收到响应 #{self.request_id}: 类型=0x{response_type:04X}, 长度={len(response_data)}, 耗时={receive_time:.2f}ms")
            self.logger.debug(f"响应 #{self.request_id} 数据: {response_data.hex()}")

            return response_type, response_data
        except Exception as e:
            self.logger.error(f"请求 #{self.request_id} 处理失败: {e}")
            self.logger.error(traceback.format_exc())  # 记录完整的异常堆栈
            raise


class FastMCPProxy:
    """FastMCP代理服务器"""

    def __init__(self, host: str = '0.0.0.0', port: int = 25577,
                 target_host: str = 'localhost', target_port: int = 25578):
        self.loggers = setup_logging()
        self.host = host
        self.port = port
        self.target_host = target_host
        self.target_port = target_port
        self.server_socket = None
        self.running = False
        self.client_handlers = {}  # 存储客户端处理器

        self.logger = self.loggers['main']
        self.packet_processor = FastMCPPacket(self.loggers)

    def start(self) -> None:
        """启动代理服务器"""
        try:
            self.logger.info(
                f"FastMCP代理服务器启动中: {self.host}:{self.port} -> {self.target_host}:{self.target_port}")

            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)

            self.running = True
            self.logger.info(f"FastMCP代理服务器已启动，等待连接...")

            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    client_id = f"{client_address[0]}_{client_address[1]}"

                    self.logger.info(f"新连接来自: {client_address}, 客户端ID={client_id}")

                    # 创建客户端处理器
                    handler = ClientHandler(client_id, client_socket, self)
                    self.client_handlers[client_id] = handler
                    threading.Thread(target=handler.start, daemon=True).start()

                except Exception as e:
                    self.logger.error(f"接受新连接时出错: {e}")

        except KeyboardInterrupt:
            self.logger.info("接收到中断信号，正在停止服务器...")
            self.stop()
        except Exception as e:
            self.logger.error(f"启动服务器时出错: {e}")
            self.logger.error(traceback.format_exc())  # 记录完整的异常堆栈
            self.stop()

    def stop(self) -> None:
        """停止代理服务器"""
        self.running = False

        # 关闭所有客户端处理器
        for client_id, handler in list(self.client_handlers.items()):
            try:
                self.logger.info(f"关闭客户端连接: 客户端ID={client_id}")
                handler.stop()
            except Exception as e:
                self.logger.error(f"关闭客户端连接时出错 (客户端ID={client_id}): {e}")

        # 关闭服务器套接字
        if self.server_socket:
            try:
                self.server_socket.close()
                self.logger.info("服务器套接字已关闭")
            except Exception as e:
                self.logger.error(f"关闭服务器套接字时出错: {e}")

        self.logger.info("FastMCP代理服务器已停止")


class ClientHandler:
    """客户端处理器"""

    def __init__(self, client_id: str, client_socket: socket.socket, proxy: FastMCPProxy):
        self.client_id = client_id
        self.client_socket = client_socket
        self.proxy = proxy
        self.server_socket = None
        self.running = False
        self.logger = proxy.loggers['handler']
        self.packet_processor = proxy.packet_processor

        # 性能监控
        self.request_count = 0
        self.total_request_time = 0

    def start(self) -> None:
        """启动客户端处理器"""
        try:
            self.logger.info(f"启动客户端处理器: 客户端ID={self.client_id}")

            # 连接到目标服务器
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.connect((self.proxy.target_host, self.proxy.target_port))

            self.running = True

            # 创建两个线程分别处理客户端到服务器和服务器到客户端的数据传输
            client_to_server = threading.Thread(
                target=self.forward_client_to_server,
                daemon=True
            )
            server_to_client = threading.Thread(
                target=self.forward_server_to_client,
                daemon=True
            )

            client_to_server.start()
            server_to_client.start()

            # 等待两个线程完成
            client_to_server.join()
            server_to_client.join()

        except Exception as e:
            self.logger.error(f"启动客户端处理器时出错 (客户端ID={self.client_id}): {e}")
            self.logger.error(traceback.format_exc())  # 记录完整的异常堆栈
            self.stop()

    def stop(self) -> None:
        """停止客户端处理器"""
        self.running = False

        # 关闭套接字
        if self.client_socket:
            try:
                self.client_socket.close()
                self.logger.info(f"客户端套接字已关闭: 客户端ID={self.client_id}")
            except Exception as e:
                self.logger.error(f"关闭客户端套接字时出错 (客户端ID={self.client_id}): {e}")

        if self.server_socket:
            try:
                self.server_socket.close()
                self.logger.info(f"服务器套接字已关闭: 客户端ID={self.client_id}")
            except Exception as e:
                self.logger.error(f"关闭服务器套接字时出错 (客户端ID={self.client_id}): {e}")

        # 从代理中移除
        if self.client_id in self.proxy.client_handlers:
            del self.proxy.client_handlers[self.client_id]

        # 记录性能统计
        if self.request_count > 0:
            avg_time = self.total_request_time / self.request_count
            self.logger.info(
                f"客户端连接统计 (客户端ID={self.client_id}): 请求总数={self.request_count}, 平均请求时间={avg_time:.2f}ms")

    def forward_client_to_server(self) -> None:
        """转发客户端到服务器的数据"""
        self.logger.info(f"开始转发客户端到服务器的数据: 客户端ID={self.client_id}")

        try:
            while self.running:
                try:
                    # 读取客户端数据包
                    start_time = time.time()
                    version, packet_type, data = self.packet_processor.read_packet(self.client_socket)
                    read_time = (time.time() - start_time) * 1000  # 毫秒

                    self.request_count += 1
                    self.logger.info(
                        f"客户端#{self.client_id} 请求 #{self.request_count}: 类型=0x{packet_type:04X}, 长度={len(data)}, 读取时间={read_time:.2f}ms")

                    # 转发到服务器
                    start_time = time.time()
                    self.packet_processor.write_packet(self.server_socket, version, packet_type, data)
                    write_time = (time.time() - start_time) * 1000  # 毫秒

                    self.total_request_time += read_time + write_time
                    self.logger.debug(f"转发请求 #{self.request_count} 到服务器, 写入时间={write_time:.2f}ms")

                except EOFError:
                    self.logger.info(f"客户端关闭连接: 客户端ID={self.client_id}")
                    break
        except Exception as e:
            self.logger.error(f"转发客户端到服务器数据时出错 (客户端ID={self.client_id}): {e}")
            self.logger.error(traceback.format_exc())  # 记录完整的异常堆栈
        finally:
            self.stop()

    def forward_server_to_client(self) -> None:
        """转发服务器到客户端的数据"""
        self.logger.info(f"开始转发服务器到客户端的数据: 客户端ID={self.client_id}")

        try:
            while self.running:
                try:
                    # 读取服务器数据包
                    start_time = time.time()
                    version, packet_type, data = self.packet_processor.read_packet(self.server_socket)
                    read_time = (time.time() - start_time) * 1000  # 毫秒

                    self.logger.info(
                        f"服务器响应客户端#{self.client_id} 请求 #{self.request_count}: 类型=0x{packet_type:04X}, 长度={len(data)}, 读取时间={read_time:.2f}ms")

                    # 转发到客户端
                    start_time = time.time()
                    self.packet_processor.write_packet(self.client_socket, version, packet_type, data)
                    write_time = (time.time() - start_time) * 1000  # 毫秒

                    self.logger.debug(f"转发响应 #{self.request_count} 到客户端, 写入时间={write_time:.2f}ms")

                except EOFError:
                    self.logger.info(f"服务器关闭连接: 客户端ID={self.client_id}")
                    break
        except Exception as e:
            self.logger.error(f"转发服务器到客户端数据时出错 (客户端ID={self.client_id}): {e}")
            self.logger.error(traceback.format_exc())  # 记录完整的异常堆栈
        finally:
            self.stop()


# 示例使用
if __name__ == "__main__":
    # 创建并启动代理服务器
    proxy = FastMCPProxy(
        host='0.0.0.0',
        port=25577,
        target_host='127.0.0.1',  # 替换为实际的FastMCP服务器地址
        target_port=5051
    )

    proxy.start()