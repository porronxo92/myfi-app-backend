"""
Servicio de Email - Envío de correos electrónicos
==================================================

Soporta múltiples proveedores:
- SMTP (Gmail, Outlook, etc.)
- SendGrid (API)
- Console (modo desarrollo - solo logging)

En modo desarrollo, los emails se loguean en la consola.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from abc import ABC, abstractmethod

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EmailProvider(ABC):
    """Clase base abstracta para proveedores de email"""

    @abstractmethod
    async def send(self, to: str, subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
        """Envía un email"""
        pass


class ConsoleEmailProvider(EmailProvider):
    """
    Proveedor de email para desarrollo.
    Solo loguea el email en la consola, no lo envía.
    """

    async def send(self, to: str, subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
        logger.info("=" * 60)
        logger.info("EMAIL (Console Provider - No enviado)")
        logger.info("=" * 60)
        logger.info(f"To: {to}")
        logger.info(f"Subject: {subject}")
        logger.info("-" * 60)
        logger.info(f"Body (text): {text_body or 'N/A'}")
        logger.info("-" * 60)
        logger.info(f"Body (HTML): {html_body[:500]}..." if len(html_body) > 500 else f"Body (HTML): {html_body}")
        logger.info("=" * 60)
        return True


class SMTPEmailProvider(EmailProvider):
    """
    Proveedor de email usando SMTP.
    Compatible con Gmail, Outlook, servidores propios, etc.
    """

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        from_email: str,
        from_name: str = "AppFinanzas",
        use_tls: bool = True
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.from_name = from_name
        self.use_tls = use_tls

    async def send(self, to: str, subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to

            # Agregar versión texto plano
            if text_body:
                msg.attach(MIMEText(text_body, "plain"))

            # Agregar versión HTML
            msg.attach(MIMEText(html_body, "html"))

            # Conectar y enviar
            if self.use_tls:
                server = smtplib.SMTP(self.host, self.port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.host, self.port)

            server.login(self.username, self.password)
            server.sendmail(self.from_email, to, msg.as_string())
            server.quit()

            logger.info(f"Email enviado exitosamente a {to}")
            return True

        except Exception as e:
            logger.error(f"Error al enviar email a {to}: {e}")
            return False


class SendGridEmailProvider(EmailProvider):
    """
    Proveedor de email usando SendGrid API.
    Requiere instalar: pip install sendgrid
    """

    def __init__(self, api_key: str, from_email: str, from_name: str = "AppFinanzas"):
        self.api_key = api_key
        self.from_email = from_email
        self.from_name = from_name

    async def send(self, to: str, subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
        try:
            # Import dinámico para no requerir sendgrid si no se usa
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Email, To, Content

            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to),
                subject=subject,
            )

            if text_body:
                message.add_content(Content("text/plain", text_body))
            message.add_content(Content("text/html", html_body))

            sg = SendGridAPIClient(self.api_key)
            response = sg.send(message)

            if response.status_code in [200, 201, 202]:
                logger.info(f"Email enviado exitosamente a {to} (SendGrid)")
                return True
            else:
                logger.error(f"Error SendGrid: {response.status_code} - {response.body}")
                return False

        except ImportError:
            logger.error("SendGrid no está instalado. Ejecuta: pip install sendgrid")
            return False
        except Exception as e:
            logger.error(f"Error al enviar email via SendGrid a {to}: {e}")
            return False


class EmailService:
    """
    Servicio principal de email.
    Selecciona automáticamente el proveedor según la configuración.
    """

    def __init__(self):
        self.provider = self._get_provider()

    def _get_provider(self) -> EmailProvider:
        """Selecciona el proveedor según la configuración"""

        # En desarrollo, usar console provider
        if settings.ENVIRONMENT == "development" and not getattr(settings, 'EMAIL_FORCE_SEND', False):
            logger.info("EmailService: Usando ConsoleEmailProvider (modo desarrollo)")
            return ConsoleEmailProvider()

        # Si hay API key de SendGrid, usarla
        sendgrid_key = getattr(settings, 'SENDGRID_API_KEY', '')
        if sendgrid_key:
            logger.info("EmailService: Usando SendGridEmailProvider")
            return SendGridEmailProvider(
                api_key=sendgrid_key,
                from_email=getattr(settings, 'EMAIL_FROM', 'noreply@appfinanzas.com'),
                from_name=getattr(settings, 'EMAIL_FROM_NAME', 'AppFinanzas')
            )

        # Si hay configuración SMTP, usarla
        smtp_host = getattr(settings, 'SMTP_HOST', '')
        if smtp_host:
            logger.info("EmailService: Usando SMTPEmailProvider")
            # PASSWORD_EMAIL_GMAIL tiene prioridad sobre SMTP_PASSWORD (App Password de Gmail)
            smtp_password = (
                getattr(settings, 'PASSWORD_EMAIL_GMAIL', '')
                or getattr(settings, 'SMTP_PASSWORD', '')
            )
            return SMTPEmailProvider(
                host=smtp_host,
                port=getattr(settings, 'SMTP_PORT', 587),
                username=getattr(settings, 'SMTP_USERNAME', ''),
                password=smtp_password,
                from_email=getattr(settings, 'EMAIL_FROM', 'noreply@appfinanzas.com'),
                from_name=getattr(settings, 'EMAIL_FROM_NAME', 'AppFinanzas'),
                use_tls=getattr(settings, 'SMTP_USE_TLS', True)
            )

        # Fallback a console
        logger.warning("EmailService: No hay proveedor configurado, usando ConsoleEmailProvider")
        return ConsoleEmailProvider()

    async def send_password_reset_email(self, to: str, reset_token: str, user_name: Optional[str] = None) -> bool:
        """
        Envía el email de restablecimiento de contraseña.

        Args:
            to: Email del destinatario
            reset_token: Token de reset (ya generado)
            user_name: Nombre del usuario (opcional)

        Returns:
            True si se envió correctamente
        """
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

        subject = "Restablecer tu contraseña - AppFinanzas"

        # Nombre para el saludo
        greeting_name = user_name or "Usuario"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 8px 8px; }}
                .button {{ display: inline-block; background: #667eea; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 20px 0; }}
                .button:hover {{ background: #5a67d8; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; font-size: 12px; color: #6b7280; }}
                .warning {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px; margin: 20px 0; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Restablecer Contraseña</h1>
                </div>
                <div class="content">
                    <p>Hola {greeting_name},</p>

                    <p>Recibimos una solicitud para restablecer la contraseña de tu cuenta en MyFi App.</p>

                    <p style="text-align: center;">
                        <a href="{reset_url}" class="button">Restablecer mi contraseña</a>
                    </p>

                    <div class="warning">
                        <strong>Importante:</strong> Este enlace expirará en 1 hora por seguridad.
                    </div>

                    <p>Si no solicitaste este cambio, puedes ignorar este email. Tu contraseña no será modificada.</p>

                    <p>Si tienes problemas con el botón, copia y pega este enlace en tu navegador:</p>
                    <p style="word-break: break-all; background: #e5e7eb; padding: 10px; border-radius: 4px; font-size: 12px;">
                        {reset_url}
                    </p>

                    <div class="footer">
                        <p>Este email fue enviado automáticamente por AppFinanzas.</p>
                        <p>Por favor, no respondas a este mensaje.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        Hola {greeting_name},

        Recibimos una solicitud para restablecer la contraseña de tu cuenta en MyFi App.

        Para restablecer tu contraseña, visita el siguiente enlace:
        {reset_url}

        IMPORTANTE: Este enlace expirará en 1 hora por seguridad.

        Si no solicitaste este cambio, puedes ignorar este email. Tu contraseña no será modificada.

        --
        MyFi App
        """

        return await self.provider.send(to, subject, html_body, text_body)


# Instancia singleton del servicio
email_service = EmailService()
