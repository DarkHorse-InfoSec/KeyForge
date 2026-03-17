"""Compliance reporting routes for KeyForge."""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
import uuid

try:
    from ..config import db, logger
    from ..security import get_current_user
    from ..models_analytics import ComplianceReport
except ImportError:
    from backend.config import db, logger
    from backend.security import get_current_user
    from backend.models_analytics import ComplianceReport

router = APIRouter(prefix="/api", tags=["compliance"])

VALID_REPORT_TYPES = ["soc2", "gdpr", "general"]


async def _analyze_credentials(user_id: str) -> dict:
    """Analyze credential security posture for a user."""
    credentials = await db.credentials.find(
        {"user_id": user_id}
    ).to_list(1000)

    total_creds = len(credentials)
    encrypted_count = sum(1 for c in credentials if c.get("api_key", ""))
    has_rotation_policy = sum(1 for c in credentials if c.get("rotation_policy"))
    overdue_rotations = sum(1 for c in credentials if c.get("rotation_overdue", False))
    has_expiration = sum(1 for c in credentials if c.get("expires_at"))

    return {
        "total_credentials": total_creds,
        "encrypted_count": encrypted_count,
        "all_encrypted": encrypted_count == total_creds if total_creds > 0 else True,
        "encryption_algorithm": "Fernet (AES-128-CBC)",
        "rotation_policy_count": has_rotation_policy,
        "rotation_policy_pct": (has_rotation_policy / total_creds * 100) if total_creds > 0 else 0,
        "overdue_rotations": overdue_rotations,
        "expiration_tracking_count": has_expiration,
        "expiration_tracking_pct": (has_expiration / total_creds * 100) if total_creds > 0 else 0,
    }


async def _analyze_user_security(user_id: str) -> dict:
    """Analyze user-level security settings."""
    user = await db.users.find_one({"_id": user_id}) or await db.users.find_one({"id": user_id})
    if not user:
        user = {}

    mfa_enabled = user.get("mfa_enabled", False)
    ip_allowlist = user.get("ip_allowlist", [])

    return {
        "mfa_enabled": mfa_enabled,
        "ip_allowlisting": len(ip_allowlist) > 0,
        "ip_allowlist_count": len(ip_allowlist),
    }


async def _analyze_audit_trail(user_id: str) -> dict:
    """Analyze audit trail completeness."""
    audit_count = await db.audit_logs.count_documents({"user_id": user_id})
    lifecycle_count = await db.lifecycle_events.count_documents({"user_id": user_id})

    credentials = await db.credentials.find(
        {"user_id": user_id}
    ).to_list(1000)

    creds_with_audit = set()
    async for log in db.audit_logs.find({"user_id": user_id}):
        cred_id = log.get("credential_id")
        if cred_id:
            creds_with_audit.add(cred_id)

    total_creds = len(credentials)
    creds_covered = len(creds_with_audit)

    return {
        "total_audit_entries": audit_count,
        "total_lifecycle_events": lifecycle_count,
        "credentials_with_audit": creds_covered,
        "audit_coverage_pct": (creds_covered / total_creds * 100) if total_creds > 0 else 0,
        "logging_active": audit_count > 0 or lifecycle_count > 0,
    }


def _generate_soc2_findings(cred_analysis: dict, security_analysis: dict, audit_analysis: dict) -> list:
    """Generate SOC2-specific compliance findings."""
    findings = []

    # CC6.1 - Logical and Physical Access Controls
    if not security_analysis["mfa_enabled"]:
        findings.append({
            "control": "CC6.1",
            "area": "Logical Access Controls",
            "status": "fail",
            "finding": "Multi-factor authentication is not enabled",
            "recommendation": "Enable MFA to strengthen access controls",
        })
    else:
        findings.append({
            "control": "CC6.1",
            "area": "Logical Access Controls",
            "status": "pass",
            "finding": "Multi-factor authentication is enabled",
        })

    # CC6.7 - Encryption
    if cred_analysis["all_encrypted"]:
        findings.append({
            "control": "CC6.7",
            "area": "Encryption of Data at Rest",
            "status": "pass",
            "finding": f"All credentials encrypted using {cred_analysis['encryption_algorithm']}",
        })
    else:
        findings.append({
            "control": "CC6.7",
            "area": "Encryption of Data at Rest",
            "status": "fail",
            "finding": "Not all credentials are encrypted",
            "recommendation": "Ensure all credentials are stored with encryption",
        })

    # CC7.2 - Monitoring
    if audit_analysis["logging_active"]:
        findings.append({
            "control": "CC7.2",
            "area": "System Monitoring",
            "status": "pass",
            "finding": f"Audit logging active with {audit_analysis['total_audit_entries']} entries",
        })
    else:
        findings.append({
            "control": "CC7.2",
            "area": "System Monitoring",
            "status": "warning",
            "finding": "No audit log entries found",
            "recommendation": "Enable and maintain audit logging for all credential operations",
        })

    # CC8.1 - Change Management
    if cred_analysis["rotation_policy_pct"] >= 100:
        findings.append({
            "control": "CC8.1",
            "area": "Change Management",
            "status": "pass",
            "finding": "All credentials have rotation policies defined",
        })
    else:
        findings.append({
            "control": "CC8.1",
            "area": "Change Management",
            "status": "warning",
            "finding": f"Only {cred_analysis['rotation_policy_pct']:.0f}% of credentials have rotation policies",
            "recommendation": "Define rotation policies for all credentials",
        })

    return findings


def _generate_gdpr_findings(cred_analysis: dict, security_analysis: dict, audit_analysis: dict) -> list:
    """Generate GDPR-specific compliance findings."""
    findings = []

    # Article 32 - Security of Processing
    findings.append({
        "article": "Article 32",
        "area": "Security of Processing",
        "status": "pass" if cred_analysis["all_encrypted"] else "fail",
        "finding": f"Encryption: {cred_analysis['encryption_algorithm']}" if cred_analysis["all_encrypted"]
                   else "Not all data is encrypted at rest",
        "recommendation": "" if cred_analysis["all_encrypted"]
                          else "Encrypt all stored credentials",
    })

    # Article 5(1)(f) - Integrity and Confidentiality
    findings.append({
        "article": "Article 5(1)(f)",
        "area": "Integrity and Confidentiality",
        "status": "pass" if security_analysis["mfa_enabled"] else "warning",
        "finding": "MFA enabled for access control" if security_analysis["mfa_enabled"]
                   else "MFA not enabled — access controls may be insufficient",
        "recommendation": "" if security_analysis["mfa_enabled"]
                          else "Enable multi-factor authentication",
    })

    # Article 30 - Records of Processing Activities
    findings.append({
        "article": "Article 30",
        "area": "Records of Processing Activities",
        "status": "pass" if audit_analysis["logging_active"] else "fail",
        "finding": f"Audit trail contains {audit_analysis['total_audit_entries']} entries"
                   if audit_analysis["logging_active"]
                   else "No processing activity records found",
        "recommendation": "" if audit_analysis["logging_active"]
                          else "Implement audit logging for all data processing activities",
    })

    return findings


def _generate_general_findings(cred_analysis: dict, security_analysis: dict, audit_analysis: dict) -> list:
    """Generate general compliance findings."""
    findings = []

    findings.append({
        "area": "Encryption",
        "status": "pass" if cred_analysis["all_encrypted"] else "fail",
        "finding": f"All credentials encrypted ({cred_analysis['encryption_algorithm']})"
                   if cred_analysis["all_encrypted"] else "Some credentials are not encrypted",
    })

    findings.append({
        "area": "Access Controls",
        "status": "pass" if security_analysis["mfa_enabled"] else "warning",
        "finding": "MFA enabled" if security_analysis["mfa_enabled"] else "MFA not enabled",
    })

    findings.append({
        "area": "IP Allowlisting",
        "status": "pass" if security_analysis["ip_allowlisting"] else "info",
        "finding": f"{security_analysis['ip_allowlist_count']} IPs in allowlist"
                   if security_analysis["ip_allowlisting"] else "No IP allowlisting configured",
    })

    findings.append({
        "area": "Rotation Policies",
        "status": "pass" if cred_analysis["rotation_policy_pct"] >= 100 else "warning",
        "finding": f"{cred_analysis['rotation_policy_pct']:.0f}% of credentials have rotation policies",
    })

    findings.append({
        "area": "Overdue Rotations",
        "status": "pass" if cred_analysis["overdue_rotations"] == 0 else "fail",
        "finding": f"{cred_analysis['overdue_rotations']} overdue rotation(s)",
    })

    findings.append({
        "area": "Audit Logging",
        "status": "pass" if audit_analysis["logging_active"] else "warning",
        "finding": f"{audit_analysis['total_audit_entries']} audit entries, "
                   f"{audit_analysis['audit_coverage_pct']:.0f}% credential coverage",
    })

    findings.append({
        "area": "Expiration Tracking",
        "status": "pass" if cred_analysis["expiration_tracking_pct"] >= 100 else "info",
        "finding": f"{cred_analysis['expiration_tracking_pct']:.0f}% of credentials have expiration tracking",
    })

    return findings


@router.post("/compliance/generate/{report_type}", response_model=dict)
async def generate_compliance_report(
    report_type: str,
    current_user: dict = Depends(get_current_user),
):
    """Generate a compliance report of the specified type."""
    if report_type not in VALID_REPORT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"report_type must be one of: {', '.join(VALID_REPORT_TYPES)}",
        )

    user_id = current_user["id"]

    cred_analysis = await _analyze_credentials(user_id)
    security_analysis = await _analyze_user_security(user_id)
    audit_analysis = await _analyze_audit_trail(user_id)

    # Generate findings based on report type
    if report_type == "soc2":
        findings = _generate_soc2_findings(cred_analysis, security_analysis, audit_analysis)
    elif report_type == "gdpr":
        findings = _generate_gdpr_findings(cred_analysis, security_analysis, audit_analysis)
    else:
        findings = _generate_general_findings(cred_analysis, security_analysis, audit_analysis)

    pass_count = sum(1 for f in findings if f.get("status") == "pass")
    fail_count = sum(1 for f in findings if f.get("status") == "fail")
    warning_count = sum(1 for f in findings if f.get("status") == "warning")

    summary = {
        "report_type": report_type,
        "total_findings": len(findings),
        "passed": pass_count,
        "failed": fail_count,
        "warnings": warning_count,
        "credential_analysis": cred_analysis,
        "security_analysis": security_analysis,
        "audit_analysis": audit_analysis,
    }

    now = datetime.now(timezone.utc)
    report_doc = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "report_type": report_type,
        "generated_at": now,
        "summary": summary,
        "findings": findings,
    }
    await db.compliance_reports.insert_one(report_doc)

    report_doc.pop("_id", None)
    return report_doc


@router.get("/compliance/reports", response_model=list[dict])
async def list_compliance_reports(
    current_user: dict = Depends(get_current_user),
):
    """List all generated compliance reports for the authenticated user."""
    reports = await db.compliance_reports.find(
        {"user_id": current_user["id"]}
    ).sort("generated_at", -1).to_list(1000)

    for r in reports:
        r.pop("_id", None)

    return reports


@router.get("/compliance/reports/{report_id}", response_model=dict)
async def get_compliance_report(
    report_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get a specific compliance report with full details."""
    report = await db.compliance_reports.find_one({
        "id": report_id,
        "user_id": current_user["id"],
    })
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report.pop("_id", None)
    return report


@router.get("/compliance/score", response_model=dict)
async def get_compliance_score(
    current_user: dict = Depends(get_current_user),
):
    """Calculate and return a compliance score (0-100)."""
    user_id = current_user["id"]

    cred_analysis = await _analyze_credentials(user_id)
    security_analysis = await _analyze_user_security(user_id)
    audit_analysis = await _analyze_audit_trail(user_id)

    score = 0
    breakdown = []

    # Has MFA: +20
    if security_analysis["mfa_enabled"]:
        score += 20
        breakdown.append({"item": "MFA enabled", "points": 20, "earned": True})
    else:
        breakdown.append({"item": "MFA enabled", "points": 20, "earned": False})

    # All credentials have rotation policy: +15
    if cred_analysis["rotation_policy_pct"] >= 100:
        score += 15
        breakdown.append({"item": "All credentials have rotation policy", "points": 15, "earned": True})
    else:
        breakdown.append({"item": "All credentials have rotation policy", "points": 15, "earned": False})

    # No overdue rotations: +10
    if cred_analysis["overdue_rotations"] == 0:
        score += 10
        breakdown.append({"item": "No overdue rotations", "points": 10, "earned": True})
    else:
        breakdown.append({"item": "No overdue rotations", "points": 10, "earned": False})

    # Has IP allowlisting: +10
    if security_analysis["ip_allowlisting"]:
        score += 10
        breakdown.append({"item": "IP allowlisting configured", "points": 10, "earned": True})
    else:
        breakdown.append({"item": "IP allowlisting configured", "points": 10, "earned": False})

    # Audit logging active: +15
    if audit_analysis["logging_active"]:
        score += 15
        breakdown.append({"item": "Audit logging active", "points": 15, "earned": True})
    else:
        breakdown.append({"item": "Audit logging active", "points": 15, "earned": False})

    # All credentials encrypted: +15
    if cred_analysis["all_encrypted"]:
        score += 15
        breakdown.append({"item": "All credentials encrypted", "points": 15, "earned": True})
    else:
        breakdown.append({"item": "All credentials encrypted", "points": 15, "earned": False})

    # Expiration tracking on all: +15
    if cred_analysis["expiration_tracking_pct"] >= 100:
        score += 15
        breakdown.append({"item": "Expiration tracking on all credentials", "points": 15, "earned": True})
    else:
        breakdown.append({"item": "Expiration tracking on all credentials", "points": 15, "earned": False})

    return {
        "score": score,
        "max_score": 100,
        "grade": "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D" if score >= 40 else "F",
        "breakdown": breakdown,
    }
