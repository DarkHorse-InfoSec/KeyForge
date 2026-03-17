"""IP allowlisting routes for KeyForge."""

import ipaddress

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.config import db, logger
from backend.models_security import IPAllowlistCreate, IPAllowlistEntry
from backend.security import get_current_user

router = APIRouter(prefix="/api", tags=["ip-allowlist"])


def _validate_ip_or_cidr(ip_string: str) -> str:
    """Validate that *ip_string* is a valid IPv4/IPv6 address or CIDR network.

    Returns the normalised string representation.
    Raises ValueError on invalid input.
    """
    try:
        # Try as a single host address first
        addr = ipaddress.ip_address(ip_string)
        return str(addr)
    except ValueError:
        pass

    try:
        # Try as a CIDR network
        network = ipaddress.ip_network(ip_string, strict=False)
        return str(network)
    except ValueError:
        raise ValueError(f"Invalid IP address or CIDR notation: {ip_string}")


def _ip_in_network(ip_str: str, network_str: str) -> bool:
    """Check whether *ip_str* falls within *network_str* (single IP or CIDR)."""
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return False

    try:
        # If the stored value is a single IP, do an exact match
        stored_addr = ipaddress.ip_address(network_str)
        return addr == stored_addr
    except ValueError:
        pass

    try:
        network = ipaddress.ip_network(network_str, strict=False)
        return addr in network
    except ValueError:
        return False


@router.post("/ip-allowlist", response_model=IPAllowlistEntry)
async def add_ip(
    body: IPAllowlistCreate,
    current_user: dict = Depends(get_current_user),
):
    """Add an IP address or CIDR range to the user's allowlist."""
    try:
        normalised = _validate_ip_or_cidr(body.ip_address)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    entry = IPAllowlistEntry(
        user_id=current_user["id"],
        ip_address=normalised,
        description=body.description,
    )

    await db.ip_allowlist.insert_one(entry.model_dump())

    logger.info(
        "IP allowlist entry added for user %s: %s",
        current_user["username"],
        normalised,
    )
    return entry


@router.get("/ip-allowlist", response_model=list[IPAllowlistEntry])
async def list_ips(current_user: dict = Depends(get_current_user)):
    """List all allowlisted IPs/CIDRs for the current user."""
    entries = await db.ip_allowlist.find({"user_id": current_user["id"]}).to_list(length=1000)

    return [IPAllowlistEntry(**e) for e in entries]


@router.delete("/ip-allowlist/{entry_id}", response_model=dict)
async def remove_ip(entry_id: str, current_user: dict = Depends(get_current_user)):
    """Remove an IP allowlist entry by its ID."""
    result = await db.ip_allowlist.delete_one({"id": entry_id, "user_id": current_user["id"]})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Allowlist entry not found")

    logger.info(
        "IP allowlist entry %s removed for user %s",
        entry_id,
        current_user["username"],
    )
    return {"message": "IP allowlist entry removed"}


@router.get("/ip-allowlist/check", response_model=dict)
async def check_ip(
    ip: str = Query(..., description="IP address to check"),
    current_user: dict = Depends(get_current_user),
):
    """Check whether a given IP address is covered by any allowlist entry."""
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid IP address")

    entries = await db.ip_allowlist.find({"user_id": current_user["id"]}).to_list(length=1000)

    for entry in entries:
        if _ip_in_network(ip, entry["ip_address"]):
            return {"allowed": True, "matched_entry": entry["ip_address"]}

    return {"allowed": False}
