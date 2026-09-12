from __future__ import annotations
from datetime import date
from enum import Enum
from pydantic import BaseModel, Field


class VendorStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"


class GetVendorInput(BaseModel):
    vendor: str = Field(..., min_length=1)


class VendorRecord(BaseModel):
    vendor_id: str
    name: str
    status: VendorStatus
    bank_account_masked: str | None = None      # NEVER store the full number
    risk_flags: list[str] = Field(default_factory=list)
    last_updated: date


class GetVendorOutput(BaseModel):
    found: bool
    vendor: VendorRecord | None = None


# --- mock vendor master data (fixtures) ---
_VENDORS: dict[str, VendorRecord] = {
    "acme supplies": VendorRecord(
        vendor_id="V-1001", name="Acme Supplies Pty Ltd", status=VendorStatus.ACTIVE,
        bank_account_masked="****6789", risk_flags=[], last_updated=date(2026, 6, 1),
    ),
    "globex trading": VendorRecord(
        vendor_id="V-1002", name="Globex Trading", status=VendorStatus.ACTIVE,
        bank_account_masked="****4321", risk_flags=["recent_bank_change"],
        last_updated=date(2026, 9, 5),
    ),
    "initech": VendorRecord(
        vendor_id="V-1003", name="Initech", status=VendorStatus.BLOCKED,
        bank_account_masked="****0000", risk_flags=["sanctions_review"],
        last_updated=date(2026, 8, 20),
    ),
}


def get_vendor_record(payload: GetVendorInput) -> GetVendorOutput:
    record = _VENDORS.get(payload.vendor.strip().lower())
    if record is None:
        return GetVendorOutput(found=False, vendor=None)
    return GetVendorOutput(found=True, vendor=record)