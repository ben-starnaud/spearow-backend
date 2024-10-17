from fastapi_mail import ConnectionConfig

conf = ConnectionConfig(
    MAIL_USERNAME="spearow.pwned@gmail.com",
    MAIL_PASSWORD="ohyp dqbf ybpq eaou",
    MAIL_FROM="spearow.pwned@gmail.com",
    MAIL_PORT=587,  # Gmail's SMTP port
    MAIL_SERVER="smtp.gmail.com",  # Gmail's SMTP server
    MAIL_FROM_NAME="Spearow",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)
