#!/usr/bin/env python3
"""
业务逻辑通知服务
提供邮件、短信等多渠道通知功能

实现需求 13.4: 通知相关业务专家
"""

import logging
import smtplib
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import requests
import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 通知请求模型
class EmailNotificationRequest(BaseModel):
    type: str
    project_id: str
    insight_id: Optional[str] = None
    title: str
    description: str
    impact_score: float
    recipients: Optional[List[EmailStr]] = None

class SmsNotificationRequest(BaseModel):
    type: str
    project_id: str
    insight_id: Optional[str] = None
    title: str
    impact_score: float
    recipients: Optional[List[str]] = None

class NotificationHistoryItem(BaseModel):
    id: str
    type: str
    channel: str
    project_id: str
    title: str
    status: str
    sent_at: datetime
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None

# 邮件配置
EMAIL_CONFIG = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "username": "your-email@gmail.com",
    "password": "your-app-password",
    "from_email": "SuperInsight Platform <noreply@superinsight.com>",
}

# 短信配置（示例使用阿里云短信服务）
SMS_CONFIG = {
    "access_key_id": "your-access-key-id",
    "access_key_secret": "your-access-key-secret",
    "sign_name": "SuperInsight",
    "template_code": "SMS_123456789",
    "endpoint": "https://dysmsapi.aliyuncs.com",
}

class EmailNotificationService:
    """邮件通知服务"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
    async def send_business_insight_email(
        self,
        recipients: List[str],
        insight_data: Dict[str, Any],
        project_id: str
    ) -> Dict[str, Any]:
        """发送业务洞察邮件通知"""
        try:
            # 构建邮件内容
            subject = f"[SuperInsight] 新的业务洞察 - {insight_data['title']}"
            
            # HTML邮件模板
            html_content = self._build_insight_email_template(insight_data, project_id)
            
            # 发送邮件
            result = await self._send_email(recipients, subject, html_content)
            
            logger.info(f"业务洞察邮件已发送: project={project_id}, recipients={len(recipients)}")
            return result
            
        except Exception as e:
            logger.error(f"发送业务洞察邮件失败: {e}")
            raise
    
    async def send_pattern_change_email(
        self,
        recipients: List[str],
        change_data: Dict[str, Any],
        project_id: str
    ) -> Dict[str, Any]:
        """发送模式变化邮件通知"""
        try:
            subject = f"[SuperInsight] 业务模式变化通知 - 项目 {project_id}"
            
            html_content = self._build_pattern_change_email_template(change_data, project_id)
            
            result = await self._send_email(recipients, subject, html_content)
            
            logger.info(f"模式变化邮件已发送: project={project_id}, recipients={len(recipients)}")
            return result
            
        except Exception as e:
            logger.error(f"发送模式变化邮件失败: {e}")
            raise
    
    async def send_rule_update_email(
        self,
        recipients: List[str],
        rule_data: Dict[str, Any],
        project_id: str
    ) -> Dict[str, Any]:
        """发送规则更新邮件通知"""
        try:
            subject = f"[SuperInsight] 业务规则更新通知 - {rule_data.get('name', '未知规则')}"
            
            html_content = self._build_rule_update_email_template(rule_data, project_id)
            
            result = await self._send_email(recipients, subject, html_content)
            
            logger.info(f"规则更新邮件已发送: project={project_id}, recipients={len(recipients)}")
            return result
            
        except Exception as e:
            logger.error(f"发送规则更新邮件失败: {e}")
            raise
    
    async def _send_email(
        self,
        recipients: List[str],
        subject: str,
        html_content: str,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """发送邮件的底层方法"""
        try:
            # 创建邮件消息
            msg = MIMEMultipart('alternative')
            msg['From'] = self.config['from_email']
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject
            
            # 添加HTML内容
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # 添加附件
            if attachments:
                for attachment in attachments:
                    self._add_attachment(msg, attachment)
            
            # 发送邮件
            with smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port']) as server:
                server.starttls()
                server.login(self.config['username'], self.config['password'])
                server.send_message(msg)
            
            return {
                "status": "success",
                "message": "邮件发送成功",
                "recipients": recipients,
                "sent_at": datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"发送邮件失败: {e}")
            return {
                "status": "error",
                "message": f"邮件发送失败: {str(e)}",
                "recipients": recipients,
                "sent_at": datetime.now().isoformat(),
            }
    
    def _add_attachment(self, msg: MIMEMultipart, attachment: Dict[str, Any]):
        """添加邮件附件"""
        try:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment['content'])
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {attachment["filename"]}'
            )
            msg.attach(part)
        except Exception as e:
            logger.error(f"添加邮件附件失败: {e}")
    
    def _build_insight_email_template(self, insight_data: Dict[str, Any], project_id: str) -> str:
        """构建业务洞察邮件模板"""
        impact_level = "高" if insight_data['impact_score'] >= 0.8 else \
                      "中" if insight_data['impact_score'] >= 0.6 else "低"
        
        impact_color = "#ff4d4f" if insight_data['impact_score'] >= 0.8 else \
                       "#faad14" if insight_data['impact_score'] >= 0.6 else "#52c41a"
        
        recommendations_html = ""
        if insight_data.get('recommendations'):
            recommendations_html = "<ul>"
            for rec in insight_data['recommendations']:
                recommendations_html += f"<li>{rec}</li>"
            recommendations_html += "</ul>"
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>SuperInsight 业务洞察通知</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #1890ff; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .insight-card {{ background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
                .impact-badge {{ display: inline-block; padding: 4px 12px; border-radius: 4px; color: white; background: {impact_color}; font-weight: bold; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                .btn {{ display: inline-block; padding: 10px 20px; background: #1890ff; color: white; text-decoration: none; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔍 SuperInsight 业务洞察</h1>
                    <p>项目: {project_id}</p>
                </div>
                
                <div class="content">
                    <div class="insight-card">
                        <h2>{insight_data['title']}</h2>
                        <p><span class="impact-badge">{impact_level}影响</span></p>
                        
                        <h3>洞察描述</h3>
                        <p>{insight_data['description']}</p>
                        
                        <h3>影响评分</h3>
                        <p>{insight_data['impact_score']:.2f} / 1.00</p>
                        
                        {f"<h3>建议措施</h3>{recommendations_html}" if recommendations_html else ""}
                        
                        <h3>检测时间</h3>
                        <p>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    </div>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="http://localhost:3000/business-logic?project={project_id}" class="btn">
                            查看详细分析
                        </a>
                    </div>
                </div>
                
                <div class="footer">
                    <p>此邮件由 SuperInsight AI 数据治理与标注平台自动发送</p>
                    <p>如需取消订阅，请联系系统管理员</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _build_pattern_change_email_template(self, change_data: Dict[str, Any], project_id: str) -> str:
        """构建模式变化邮件模板"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>SuperInsight 模式变化通知</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #52c41a; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .change-card {{ background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                .btn {{ display: inline-block; padding: 10px 20px; background: #52c41a; color: white; text-decoration: none; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📈 业务模式变化通知</h1>
                    <p>项目: {project_id}</p>
                </div>
                
                <div class="content">
                    <div class="change-card">
                        <h2>模式变化详情</h2>
                        <p>{change_data.get('description', '检测到业务模式发生变化')}</p>
                        
                        <h3>变化类型</h3>
                        <p>{change_data.get('type', '未知')}</p>
                        
                        <h3>检测时间</h3>
                        <p>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    </div>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="http://localhost:3000/business-logic?project={project_id}&tab=patterns" class="btn">
                            查看模式分析
                        </a>
                    </div>
                </div>
                
                <div class="footer">
                    <p>此邮件由 SuperInsight AI 数据治理与标注平台自动发送</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _build_rule_update_email_template(self, rule_data: Dict[str, Any], project_id: str) -> str:
        """构建规则更新邮件模板"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>SuperInsight 规则更新通知</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #faad14; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .rule-card {{ background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                .btn {{ display: inline-block; padding: 10px 20px; background: #faad14; color: white; text-decoration: none; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⚙️ 业务规则更新通知</h1>
                    <p>项目: {project_id}</p>
                </div>
                
                <div class="content">
                    <div class="rule-card">
                        <h2>{rule_data.get('name', '未知规则')}</h2>
                        
                        <h3>规则描述</h3>
                        <p>{rule_data.get('description', '无描述')}</p>
                        
                        <h3>规则类型</h3>
                        <p>{rule_data.get('rule_type', '未知')}</p>
                        
                        <h3>置信度</h3>
                        <p>{rule_data.get('confidence', 0):.2f}</p>
                        
                        <h3>更新时间</h3>
                        <p>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    </div>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="http://localhost:3000/business-logic?project={project_id}&tab=rules" class="btn">
                            查看规则详情
                        </a>
                    </div>
                </div>
                
                <div class="footer">
                    <p>此邮件由 SuperInsight AI 数据治理与标注平台自动发送</p>
                </div>
            </div>
        </body>
        </html>
        """

class SmsNotificationService:
    """短信通知服务"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    async def send_business_insight_sms(
        self,
        recipients: List[str],
        insight_data: Dict[str, Any],
        project_id: str
    ) -> Dict[str, Any]:
        """发送业务洞察短信通知"""
        try:
            # 构建短信内容
            impact_level = "高" if insight_data['impact_score'] >= 0.8 else \
                          "中" if insight_data['impact_score'] >= 0.6 else "低"
            
            message = f"【SuperInsight】项目{project_id}发现{impact_level}影响业务洞察：{insight_data['title'][:20]}...，请及时查看处理。"
            
            # 发送短信
            results = []
            for phone in recipients:
                result = await self._send_sms(phone, message)
                results.append(result)
            
            logger.info(f"业务洞察短信已发送: project={project_id}, recipients={len(recipients)}")
            return {
                "status": "success",
                "message": "短信发送完成",
                "results": results,
                "sent_at": datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"发送业务洞察短信失败: {e}")
            raise
    
    async def send_pattern_change_sms(
        self,
        recipients: List[str],
        change_data: Dict[str, Any],
        project_id: str
    ) -> Dict[str, Any]:
        """发送模式变化短信通知"""
        try:
            message = f"【SuperInsight】项目{project_id}业务模式发生变化，请及时查看分析结果。"
            
            results = []
            for phone in recipients:
                result = await self._send_sms(phone, message)
                results.append(result)
            
            logger.info(f"模式变化短信已发送: project={project_id}, recipients={len(recipients)}")
            return {
                "status": "success",
                "message": "短信发送完成",
                "results": results,
                "sent_at": datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"发送模式变化短信失败: {e}")
            raise
    
    async def _send_sms(self, phone: str, message: str) -> Dict[str, Any]:
        """发送短信的底层方法"""
        try:
            # 这里使用阿里云短信服务API
            # 实际实现需要根据具体的短信服务提供商调整
            
            # 模拟短信发送
            await asyncio.sleep(0.1)  # 模拟网络延迟
            
            # 简单的手机号验证
            if not phone or len(phone) != 11 or not phone.startswith('1'):
                return {
                    "phone": phone,
                    "status": "error",
                    "message": "无效的手机号码",
                }
            
            return {
                "phone": phone,
                "status": "success",
                "message": "短信发送成功",
                "message_id": f"sms_{datetime.now().timestamp()}",
            }
            
        except Exception as e:
            logger.error(f"发送短信到 {phone} 失败: {e}")
            return {
                "phone": phone,
                "status": "error",
                "message": f"短信发送失败: {str(e)}",
            }

class NotificationHistoryService:
    """通知历史记录服务"""
    
    def __init__(self):
        # 简单的内存存储，实际应该使用数据库
        self.history: List[NotificationHistoryItem] = []
    
    def add_notification_record(
        self,
        notification_type: str,
        channel: str,
        project_id: str,
        title: str,
        status: str,
        error_message: Optional[str] = None
    ) -> str:
        """添加通知记录"""
        record_id = f"notif_{datetime.now().timestamp()}"
        
        record = NotificationHistoryItem(
            id=record_id,
            type=notification_type,
            channel=channel,
            project_id=project_id,
            title=title,
            status=status,
            sent_at=datetime.now(),
            error_message=error_message,
        )
        
        self.history.append(record)
        return record_id
    
    def get_notification_history(
        self,
        project_id: Optional[str] = None,
        channel: Optional[str] = None,
        limit: int = 100
    ) -> List[NotificationHistoryItem]:
        """获取通知历史记录"""
        filtered_history = self.history
        
        if project_id:
            filtered_history = [h for h in filtered_history if h.project_id == project_id]
        
        if channel:
            filtered_history = [h for h in filtered_history if h.channel == channel]
        
        # 按时间倒序排列
        filtered_history.sort(key=lambda x: x.sent_at, reverse=True)
        
        return filtered_history[:limit]

# 全局服务实例
email_service = EmailNotificationService(EMAIL_CONFIG)
sms_service = SmsNotificationService(SMS_CONFIG)
history_service = NotificationHistoryService()

# API路由
router = APIRouter(prefix="/api/notifications", tags=["notifications"])

@router.post("/email")
async def send_email_notification(
    request: EmailNotificationRequest,
    background_tasks: BackgroundTasks
):
    """发送邮件通知"""
    try:
        # 获取默认收件人（如果未指定）
        recipients = request.recipients or ["admin@example.com"]  # 默认管理员邮箱
        
        # 记录通知历史
        record_id = history_service.add_notification_record(
            notification_type=request.type,
            channel="email",
            project_id=request.project_id,
            title=request.title,
            status="sending",
        )
        
        # 异步发送邮件
        if request.type == "business_insight":
            background_tasks.add_task(
                email_service.send_business_insight_email,
                recipients,
                {
                    "title": request.title,
                    "description": request.description,
                    "impact_score": request.impact_score,
                    "recommendations": [],  # 可以从请求中获取
                },
                request.project_id
            )
        
        return {
            "message": "邮件通知已发送",
            "record_id": record_id,
            "recipients": recipients,
        }
        
    except Exception as e:
        logger.error(f"发送邮件通知失败: {e}")
        raise HTTPException(status_code=500, detail=f"发送邮件通知失败: {str(e)}")

@router.post("/sms")
async def send_sms_notification(
    request: SmsNotificationRequest,
    background_tasks: BackgroundTasks
):
    """发送短信通知"""
    try:
        # 获取默认收件人（如果未指定）
        recipients = request.recipients or ["13800138000"]  # 默认管理员手机
        
        # 记录通知历史
        record_id = history_service.add_notification_record(
            notification_type=request.type,
            channel="sms",
            project_id=request.project_id,
            title=request.title,
            status="sending",
        )
        
        # 异步发送短信
        if request.type == "business_insight":
            background_tasks.add_task(
                sms_service.send_business_insight_sms,
                recipients,
                {
                    "title": request.title,
                    "impact_score": request.impact_score,
                },
                request.project_id
            )
        
        return {
            "message": "短信通知已发送",
            "record_id": record_id,
            "recipients": recipients,
        }
        
    except Exception as e:
        logger.error(f"发送短信通知失败: {e}")
        raise HTTPException(status_code=500, detail=f"发送短信通知失败: {str(e)}")

@router.get("/history")
async def get_notification_history(
    project_id: Optional[str] = None,
    channel: Optional[str] = None,
    limit: int = 100
):
    """获取通知历史记录"""
    try:
        history = history_service.get_notification_history(
            project_id=project_id,
            channel=channel,
            limit=limit
        )
        
        return {
            "history": [h.dict() for h in history],
            "total": len(history),
        }
        
    except Exception as e:
        logger.error(f"获取通知历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取通知历史失败: {str(e)}")

# 导出主要组件
__all__ = [
    'email_service',
    'sms_service',
    'history_service',
    'router',
    'EmailNotificationService',
    'SmsNotificationService',
    'NotificationHistoryService',
]