"""
Flora OS — Daily Morning Brief Email Sender
Sends personalized HTML email with yesterday's top news to subscribed users.
"""

import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("services.email_sender")


# ── HTML Email Template ───────────────────────────────────────────────────────

def _build_email_html(
    user_name: str,
    morning_message: str,
    date_str: str,
    articles: list[dict],
    weather: Optional[dict],
    market: Optional[dict],
    jobs: Optional[list[dict]] = None,
) -> str:
    first_name = user_name.split()[0] if user_name else "there"

    # Articles section
    articles_html = ""
    for i, art in enumerate(articles[:8], 1):
        score = art.get("importance_score", 5)
        badge_color = "#7c6af7" if score >= 8 else "#38bdf8" if score >= 6 else "#64748b"
        articles_html += f"""
        <tr>
          <td style="padding:16px 0;border-bottom:1px solid #1e293b;">
            <div style="display:flex;align-items:flex-start;gap:12px;">
              <div style="background:{badge_color};color:#fff;border-radius:4px;
                          padding:2px 8px;font-size:11px;font-weight:700;
                          white-space:nowrap;margin-top:2px;">
                #{i}
              </div>
              <div>
                <div style="font-size:15px;font-weight:600;color:#f1f5f9;
                            margin-bottom:6px;line-height:1.4;">
                  <a href="{art.get('url','#')}" style="color:#f1f5f9;text-decoration:none;">
                    {art.get('title','')}
                  </a>
                </div>
                <div style="font-size:13px;color:#94a3b8;line-height:1.6;margin-bottom:8px;">
                  {art.get('summary','')}
                </div>
                <div style="font-size:11px;color:#64748b;">
                  {art.get('source','')} &nbsp;·&nbsp; {art.get('category','')} &nbsp;·&nbsp;
                  {art.get('read_time_minutes',3)} min read
                </div>
              </div>
            </div>
          </td>
        </tr>"""

    # Weather section
    weather_html = ""
    if weather:
        weather_html = f"""
        <tr>
          <td style="padding:12px 16px;background:#1e293b;border-radius:8px;margin-bottom:16px;">
            <span style="font-size:20px;">{weather.get('icon','')}</span>
            <strong style="color:#f1f5f9;">{weather.get('city','')} — {weather.get('temp_c','')}°C</strong>
            <span style="color:#94a3b8;font-size:13px;margin-left:8px;">
              {weather.get('description','')} · Feels {weather.get('feels_like','')}°C
            </span>
          </td>
        </tr>
        <tr><td style="height:16px;"></td></tr>"""

    # Market section
    market_html = ""
    if market and market.get("stocks"):
        rows = ""
        for s in market["stocks"][:5]:
            pct = s.get("change_pct", 0)
            color = "#4ade80" if pct >= 0 else "#f87171"
            arrow = "▲" if pct >= 0 else "▼"
            rows += f"""
            <tr>
              <td style="padding:6px 0;color:#f1f5f9;font-weight:600;">{s['ticker']}</td>
              <td style="padding:6px 8px;color:#94a3b8;font-size:13px;">{s.get('name','')[:20]}</td>
              <td style="padding:6px 0;text-align:right;color:#f1f5f9;">${s['price']:,.2f}</td>
              <td style="padding:6px 0 6px 8px;text-align:right;color:{color};font-size:13px;">
                {arrow} {abs(pct):.2f}%
              </td>
            </tr>"""
        market_html = f"""
        <tr>
          <td style="padding:20px 0 8px;">
            <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                        letter-spacing:0.1em;color:#64748b;margin-bottom:12px;">
              Market Snapshot
            </div>
            <table width="100%" cellpadding="0" cellspacing="0">{rows}</table>
          </td>
        </tr>"""

    # Jobs section
    jobs_html = ""
    if jobs:
        job_rows = ""
        for j in jobs[:8]:
            job_rows += f"""
            <tr>
              <td style="padding:12px 0;border-bottom:1px solid #1e293b;">
                <div style="font-size:14px;font-weight:600;color:#f1f5f9;margin-bottom:4px;">
                  <a href="{j.get('url','#')}" style="color:#7c6af7;text-decoration:none;">
                    {j.get('title','')}
                  </a>
                </div>
                <div style="font-size:12px;color:#94a3b8;margin-bottom:4px;">
                  {j.get('company','')} &nbsp;·&nbsp; {j.get('location','')}
                  &nbsp;·&nbsp; <span style="color:#4ade80;">{j.get('experience','0–1 yr')}</span>
                </div>
                <div style="font-size:11px;color:#64748b;">{j.get('source','')}</div>
              </td>
            </tr>"""
        jobs_html = f"""
        <tr><td style="height:24px;"></td></tr>
        <tr>
          <td>
            <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                        letter-spacing:0.1em;color:#64748b;margin-bottom:12px;">
              &#128188; Data Science &amp; AIML Jobs · Fresher (0–1 yr)
            </div>
            <table width="100%" cellpadding="0" cellspacing="0">{job_rows}</table>
          </td>
        </tr>"""

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Flora OS — Morning Brief</title>
</head>
<body style="margin:0;padding:0;background:#0f172a;font-family:-apple-system,BlinkMacSystemFont,
             'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;min-height:100vh;">
    <tr>
      <td align="center" style="padding:40px 20px;">
        <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#7c6af7,#38bdf8);border-radius:12px 12px 0 0;
                        padding:32px;text-align:center;">
              <div style="font-size:36px;margin-bottom:8px;">🌿</div>
              <div style="font-size:28px;font-weight:800;color:#ffffff;letter-spacing:-0.04em;">
                Flora OS
              </div>
              <div style="font-size:14px;color:rgba(255,255,255,0.8);margin-top:4px;">
                Your Morning Brief · {date_str}
              </div>
            </td>
          </tr>

          <!-- Greeting -->
          <tr>
            <td style="background:#1e293b;padding:28px 32px;">
              <div style="font-size:22px;font-weight:700;color:#f1f5f9;margin-bottom:8px;">
                Good morning, {first_name} ☀️
              </div>
              <div style="font-size:15px;color:#94a3b8;line-height:1.6;">
                {morning_message}
              </div>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="background:#0f172a;padding:0 32px 32px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr><td style="height:24px;"></td></tr>

                {weather_html}

                <!-- Top Stories heading -->
                <tr>
                  <td style="padding-bottom:4px;">
                    <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                                letter-spacing:0.1em;color:#64748b;">
                      Top Stories · Last 24 Hours
                    </div>
                  </td>
                </tr>

                {articles_html}

                {market_html}

                {jobs_html}

                <!-- Footer CTA -->
                <tr><td style="height:32px;"></td></tr>
                <tr>
                  <td style="text-align:center;">
                    <a href="{settings.app_base_url}" style="display:inline-block;
                       background:linear-gradient(135deg,#7c6af7,#38bdf8);
                       color:#ffffff;font-weight:700;font-size:14px;
                       padding:12px 32px;border-radius:8px;text-decoration:none;">
                      Open Full Brief →
                    </a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#1e293b;border-radius:0 0 12px 12px;
                        padding:20px 32px;text-align:center;">
              <div style="font-size:12px;color:#64748b;line-height:1.6;">
                You're receiving this because you activated Flora OS daily brief.<br>
                To stop receiving emails, open Flora OS → Settings → Deactivate Daily Brief.
              </div>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


# ── Send Function ─────────────────────────────────────────────────────────────

def send_morning_brief(
    to_email: str,
    user_name: str,
    morning_message: str,
    articles: list[dict],
    weather: Optional[dict] = None,
    market: Optional[dict] = None,
    jobs: Optional[list[dict]] = None,
) -> bool:
    """Send the morning brief email. Returns True on success."""
    if not settings.smtp_email or not settings.smtp_password:
        logger.warning("SMTP not configured — skipping email to %s", to_email)
        return False

    date_str = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%A, %B %d, %Y")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🌿 Your Flora Morning Brief — {datetime.now(timezone.utc).strftime('%b %d')}"
    msg["From"] = f"Flora OS <{settings.smtp_email}>"
    msg["To"] = to_email

    html_body = _build_email_html(
        user_name=user_name,
        morning_message=morning_message or "Here's what happened in the world yesterday. Stay informed, stay ahead.",
        date_str=date_str,
        articles=articles,
        weather=weather,
        market=market,
        jobs=jobs,
    )

    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(settings.smtp_email, settings.smtp_password)
            smtp.sendmail(settings.smtp_email, to_email, msg.as_string())
        logger.info("Morning brief sent to %s", to_email)
        return True
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to_email, exc)
        return False
