import json
import logging
import time
from typing import Dict, Any, Optional
import requests
from sseclient import SSEClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sse_mcp.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SSEMCPLogger:
    """客户端SSE请求MCP服务的记录器"""

    def __init__(self, mcp_endpoint: str, auth_token: str,
                 client_id: str, subscription_topics: list):
        """
        初始化SSE-MCP记录器

        Args:
            mcp_endpoint: MCP服务的SSE端点URL
            auth_token: 认证令牌
            client_id: 客户端唯一标识
            subscription_topics: 订阅的主题列表
        """
        self.mcp_endpoint = mcp_endpoint
        self.auth_token = auth_token
        self.client_id = client_id
        self.subscription_topics = subscription_topics
        self.session = None
        self.client = None
        self.session_id = None

    def _create_headers(self) -> Dict[str, str]:
        """创建请求头"""
        return {
            'Accept': 'text/event-stream',
            'Authorization': f'Bearer {self.auth_token}',
            'Client-Type': f'python-sse-client-v1.0',
            'Subscription': json.dumps({"topics": self.subscription_topics})
        }

    def _log_event(self, event_type: str, details: Dict[str, Any]):
        """
        记录SSE事件

        Args:
            event_type: 事件类型
            details: 事件详情
        """
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": "INFO",
            "event": event_type,
            "client_id": self.client_id,
            "mcp_service": self.mcp_endpoint,
            "session_id": self.session_id,
            **details
        }
        logger.info(json.dumps(log_entry))

    def connect(self):
        """建立与MCP服务的SSE连接"""
        try:
            self._log_event("sse_connection_init", {
                "subscription_topics": self.subscription_topics
            })

            self.session = requests.Session()
            self.client = SSEClient(self.mcp_endpoint, headers=self._create_headers(),
                                    session=self.session)

            # 记录连接成功
            self._log_event("sse_connection_established", {})

            # 处理初始消息获取session_id
            for event in self.client:
                if event.event == 'session-init':
                    try:
                        data = json.loads(event.data)
                        self.session_id = data.get('session_id')
                        self._log_event("session_initialized", {
                            "session_id": self.session_id
                        })
                        break
                    except json.JSONDecodeError:
                        self._log_event("session_init_error", {
                            "error": "Invalid JSON format",
                            "data": event.data
                        })
        except Exception as e:
            self._log_event("connection_failed", {
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise

    def start_listening(self, message_processor=None):
        """
        开始监听MCP服务的消息

        Args:
            message_processor: 可选的消息处理函数
        """
        if not self.client:
            self.connect()

        self._log_event("sse_listening_started", {})

        try:
            for event in self.client:
                if event.event:
                    # 记录消息接收
                    try:
                        data = json.loads(event.data) if event.data else {}
                    except json.JSONDecodeError:
                        data = {"raw_data": event.data}

                    message_details = {
                        "event_type": event.event,
                        "message_id": event.id,
                        "data": data,
                        "retry": getattr(event, 'retry', None)
                    }

                    self._log_event("sse_message_received", message_details)

                    # 调用外部处理器
                    if message_processor:
                        try:
                            message_processor(event)
                        except Exception as e:
                            self._log_event("message_processing_error", {
                                "error": str(e),
                                "event_type": event.event
                            })
        except requests.exceptions.RequestException as e:
            self._log_event("connection_error", {
                "error": str(e),
                "error_type": type(e).__name__
            })
            # 可以添加重连逻辑
            raise
        except Exception as e:
            self._log_event("unexpected_error", {
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise
        finally:
            self._log_event("sse_listening_stopped", {})

    def disconnect(self):
        """断开与MCP服务的连接"""
        if self.client:
            try:
                self.client.close()
                self._log_event("sse_connection_closed", {})
            except Exception as e:
                self._log_event("connection_close_error", {
                    "error": str(e)
                })
            finally:
                self.client = None
                self.session = None


if __name__ == "__main__":
    # 使用示例
    MCP_ENDPOINT = "https://mcp-service.com/events"
    AUTH_TOKEN = "your-auth-token"
    CLIENT_ID = "client-12345"
    SUBSCRIPTION_TOPICS = ["config-updates", "service-status"]


    def custom_processor(event):
        """自定义消息处理器"""
        if event.event == 'config-update':
            try:
                config_data = json.loads(event.data)
                # 处理配置更新逻辑
                print(f"配置更新: {config_data}")
            except json.JSONDecodeError:
                print(f"无效配置数据格式: {event.data}")


    logger = SSEMCPLogger(MCP_ENDPOINT, AUTH_TOKEN, CLIENT_ID, SUBSCRIPTION_TOPICS)

    try:
        logger.connect()
        logger.start_listening(custom_processor)
    except KeyboardInterrupt:
        logger.disconnect()
        print("程序已停止")
    except Exception as e:
        print(f"发生错误: {e}")
        logger.disconnect()