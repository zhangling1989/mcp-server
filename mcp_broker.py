import json
import logging
import time
from typing import Dict, Any, Optional, Tuple
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import socketserver
import requests
from sseclient import SSEClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sse_mcp_proxy.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SSEProxyHandler(BaseHTTPRequestHandler):
    """处理客户端到MCP服务的SSE代理请求"""

    protocol_version = 'HTTP/1.1'

    def __init__(self, request, client_address, server, mcp_config: Dict[str, Any]):
        self.mcp_config = mcp_config
        super().__init__(request, client_address, server)

    def _log_proxy_event(self, event_type: str, details: Dict[str, Any]):
        """记录代理事件"""
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": "INFO",
            "event": event_type,
            "client_ip": self.client_address[0],
            "proxy_port": self.server.server_address[1],
            **details
        }
        logger.info(json.dumps(log_entry))

    def _log_request(self):
        """记录客户端请求"""
        headers = dict(self.headers)
        self._log_proxy_event("client_request", {
            "method": self.command,
            "path": self.path,
            "headers": headers,
            "remote_addr": self.client_address[0]
        })

    def _log_response(self, response_event: Dict[str, Any]):
        """记录服务端响应事件"""
        self._log_proxy_event("server_response", response_event)

    def do_GET(self):
        """处理GET请求并代理到MCP服务"""
        self._log_request()

        # 准备转发到MCP的请求
        mcp_url = f"{self.mcp_config['base_url']}{self.path}"
        headers = dict(self.headers)

        # 添加或修改特定请求头
        headers['Host'] = self.mcp_config['host']
        if 'Authorization' not in headers and 'auth_token' in self.mcp_config:
            headers['Authorization'] = f"Bearer {self.mcp_config['auth_token']}"

        try:
            # 连接到MCP服务
            self._log_proxy_event("connecting_to_mcp", {
                "mcp_url": mcp_url
            })

            # 初始化SSE客户端连接到MCP
            sse_client = SSEClient(mcp_url, headers=headers,
                                   verify=self.mcp_config.get('verify_ssl', True))

            # 向客户端发送响应头
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.end_headers()

            # 代理转发SSE事件
            for event in sse_client:
                if event.data or event.event:
                    # 构建要发送给客户端的SSE消息
                    sse_message = ""
                    if event.id:
                        sse_message += f"id: {event.id}\n"
                    if event.event:
                        sse_message += f"event: {event.event}\n"
                    if event.data:
                        sse_message += f"data: {event.data}\n"
                    sse_message += "\n"

                    # 记录服务端响应
                    try:
                        data_obj = json.loads(event.data) if event.data else {}
                    except json.JSONDecodeError:
                        data_obj = {"raw_data": event.data}

                    self._log_response({
                        "event_type": event.event,
                        "message_id": event.id,
                        "data": data_obj
                    })

                    # 发送到客户端
                    try:
                        self.wfile.write(sse_message.encode('utf-8'))
                        self.wfile.flush()
                    except Exception as e:
                        self._log_proxy_event("client_disconnect", {
                            "error": str(e),
                            "client_ip": self.client_address[0]
                        })
                        break
        except Exception as e:
            self._log_proxy_event("proxy_error", {
                "error": str(e),
                "mcp_url": mcp_url
            })
            self.send_error(500, f"Proxy Error: {str(e)}")

    def log_message(self, format, *args):
        """禁用默认日志记录，使用自定义日志"""
        pass


class ThreadingSSEProxyServer(ThreadingHTTPServer, socketserver.ThreadingMixIn):
    """多线程SSE代理服务器"""
    daemon_threads = True

    def __init__(self, server_address: Tuple[str, int], mcp_config: Dict[str, Any]):
        def handler(*args):
            SSEProxyHandler(*args, mcp_config=mcp_config)

        super().__init__(server_address, handler)
        self.mcp_config = mcp_config
        self.allow_reuse_address = True


def run_proxy_server(proxy_host: str = 'localhost', proxy_port: int = 8080,
                     mcp_base_url: str = 'https://mcp-service.com',
                     mcp_host: str = 'mcp-service.com',
                     auth_token: Optional[str] = None,
                     verify_ssl: bool = True):
    """
    运行SSE代理服务器

    Args:
        proxy_host: 代理服务器监听地址
        proxy_port: 代理服务器监听端口
        mcp_base_url: MCP服务基础URL
        mcp_host: MCP服务主机名
        auth_token: 访问MCP服务的认证令牌
        verify_ssl: 是否验证SSL证书
    """
    mcp_config = {
        "base_url": mcp_base_url,
        "host": mcp_host,
        "auth_token": auth_token,
        "verify_ssl": verify_ssl
    }

    server_address = (proxy_host, proxy_port)
    httpd = ThreadingSSEProxyServer(server_address, mcp_config)

    logger.info(f"SSE Proxy Server running on {proxy_host}:{proxy_port}, "
                f"proxying to {mcp_base_url}")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        logger.info("SSE Proxy Server stopped")


if __name__ == "__main__":
    # 使用示例
    run_proxy_server(
        proxy_host='localhost',
        proxy_port=8080,
        mcp_base_url='http://10.0.1.21:5050/sse/',
        mcp_host='10.0.1.21',
        auth_token='your-auth-token',
        verify_ssl=True
    )