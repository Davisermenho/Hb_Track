"""Templates aprovados para envio de emails via Resend (modo standalone)."""

import logging
import os
from typing import Optional

import resend

logger = logging.getLogger(__name__)

FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL") or os.getenv("EMAIL_FROM") or "suporte@handballtrack.app"
FROM_NAME = os.getenv("RESEND_FROM_NAME") or os.getenv("EMAIL_FROM_NAME") or "HB Track"


def _welcome_html(nome_usuario: Optional[str], link_ativacao: str) -> str:
    saudacao = f"Olá, {nome_usuario}" if nome_usuario else "Olá,"
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Seja bem-vindo(a) ao HB Track!</title>
    <style>
        body {{
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #F8FAFC;
            color: #0F172A;
            line-height: 1.4;
            font-size: 14px;
            font-weight: 400;
        }}
        .container {{
            max-width: 600px;
            margin: 40px auto;
            background-color: #FFFFFF;
            padding: 32px;
            border-radius: 8px;
            box-shadow: 0 1px 2px rgba(15,23,42,0.1);
            border: 1px solid rgba(51,65,85,0.12);
        }}
        .header {{
            text-align: center;
            margin-bottom: 24px;
        }}
        .logo {{
            font-size: 28px;
            font-weight: 600;
            color: #0F172A;
            text-decoration: none;
            display: block;
        }}
        .title {{
            font-size: 22px;
            font-weight: 600;
            margin-top: 24px;
            color: #0F172A;
        }}
        .text {{
            font-size: 14px;
            font-weight: 400;
            margin-bottom: 16px;
            color: #475569;
        }}
        .highlight-link-container {{
            text-align: center;
            margin-top: 32px;
            margin-bottom: 32px;
        }}
        .highlight-link {{
            display: inline-block;
            padding: 12px 24px;
            background-color: #0F172A;
            color: #F8FAFC;
            text-decoration: none;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 500;
            line-height: 1.2;
            transition: background-color 150ms ease-out;
        }}
        .highlight-link:hover {{
            background-color: #334155;
        }}
        .footer {{
            margin-top: 40px;
            text-align: center;
            font-size: 12px;
            color: #64748B;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <span class="logo">HB TRACK</span>
        </div>
        <p class="title">Seja bem-vindo(a) ao HB Track.</p>
        <p class="text">{saudacao}</p>
        <p class="text">Sua conta foi criada com sucesso e já está pronta para uso.</p>
        <p class="text">O HB Track é a plataforma oficial para organização, acompanhamento e análise da rotina esportiva da sua equipe, reunindo informações de treinos, jogos e evolução individual.</p>
        <p class="text">Clique no link abaixo para acessar a plataforma e concluir seu primeiro acesso.</p>
        <div class="highlight-link-container">
            <a href="{link_ativacao}" class="highlight-link">Acessar plataforma</a>
        </div>
        <p class="text">O link expira em 48 horas por segurança.</p>
        <p class="text">Após o login, você verá apenas as áreas compatíveis com o seu perfil no sistema.</p>
        <p class="text">Em caso de dúvidas, procure a comissão técnica, a coordenação da equipe ou o suporte do sistema.</p>
        <div class="footer">
            <p>&copy; 2024 HB Track. Todos os direitos reservados.</p>
        </div>
    </div>
</body>
</html>"""


def _reset_html(link_token: str, nome_usuario: Optional[str] = None) -> str:
    saudacao = f"Olá, {nome_usuario}" if nome_usuario else "Olá,"
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Redefinição de senha - HB Track</title>
    <style>
        body {{
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #F8FAFC;
            color: #0F172A;
            line-height: 1.4;
            font-size: 14px;
            font-weight: 400;
        }}
        .container {{
            max-width: 600px;
            margin: 40px auto;
            background-color: #FFFFFF;
            padding: 32px;
            border-radius: 8px;
            box-shadow: 0 1px 2px rgba(15,23,42,0.1);
            border: 1px solid rgba(51,65,85,0.12);
        }}
        .header {{
            text-align: center;
            margin-bottom: 24px;
        }}
        .logo {{
            font-size: 28px;
            font-weight: 600;
            color: #0F172A;
            text-decoration: none;
            display: block;
        }}
        .title {{
            font-size: 22px;
            font-weight: 600;
            margin-top: 24px;
            color: #0F172A;
        }}
        .text {{
            font-size: 14px;
            font-weight: 400;
            margin-bottom: 16px;
            color: #475569;
        }}
        .highlight-link-container {{
            text-align: center;
            margin-top: 32px;
            margin-bottom: 32px;
        }}
        .highlight-link {{
            display: inline-block;
            padding: 12px 24px;
            background-color: #0F172A;
            color: #F8FAFC;
            text-decoration: none;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 500;
            line-height: 1.2;
            transition: background-color 150ms ease-out;
        }}
        .highlight-link:hover {{
            background-color: #334155;
        }}
        .footer {{
            margin-top: 40px;
            text-align: center;
            font-size: 12px;
            color: #64748B;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <span class="logo">HB TRACK</span>
        </div>
        <p class="title">Redefinição de senha solicitada</p>
        <p class="text">{saudacao}</p>
        <p class="text">Recebemos uma solicitação para redefinir a senha da sua conta no HB Track.</p>
        <p class="text">Para criar uma nova senha com segurança, clique no link abaixo:</p>
        <div class="highlight-link-container">
            <a href="{link_token}" class="highlight-link">Redefinir senha</a>
        </div>
        <p class="text">O link expira em 1 hora por segurança.</p>
        <p class="text">Se você não solicitou essa ação, ignore este email. Nenhuma alteração será realizada.</p>
        <div class="footer">
            <p>&copy; 2024 HB Track. Todos os direitos reservados.</p>
        </div>
    </div>
</body>
</html>"""


def _send_email(to: str, subject: str, html: str) -> bool:
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        logger.error("RESEND_API_KEY não configurada; email não enviado")
        return False

    try:
        resend.api_key = api_key
        payload = {
            "from": f"{FROM_NAME} <{FROM_EMAIL}>",
            "to": to,
            "subject": subject,
            "html": html,
        }
        resend.Emails.send(payload)
        logger.info("Email enviado via Resend", extra={"to": to, "subject": subject})
        return True
    except Exception as exc:
        logger.error(f"Erro ao enviar email via Resend para {to}: {exc}")
        return False


def enviar_email_boas_vindas(email_destino: str, nome_usuario: Optional[str], link_ativacao: str) -> bool:
    """Envia email de boas-vindas (48h)."""
    html = _welcome_html(nome_usuario, link_ativacao)
    return _send_email(
        to=email_destino,
        subject="Bem-vindo ao HB Track",
        html=html,
    )


def enviar_email_recuperacao(email_destino: str, link_token: str, nome_usuario: Optional[str] = None) -> bool:
    """Envia email de recuperação de senha (1h)."""
    html = _reset_html(link_token, nome_usuario)
    return _send_email(
        to=email_destino,
        subject="Redefinição de senha - HB Track",
        html=html,
    )
