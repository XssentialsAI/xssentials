"""Pydantic models for D-Tools Cloud API.

Phase 1: skeleton ClientLite / ClientDetail.
Phase 2: full ClientDetail with address, contact, and all detail-only fields.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class Address(BaseModel):
    """Billing or site address block (billingAddress / siteAddresses[])."""

    model_config = ConfigDict(extra="ignore")

    name: Optional[str] = None
    addressLine1: Optional[str] = None
    addressLine2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postalCode: Optional[str] = None
    country: Optional[str] = None


class Contact(BaseModel):
    """Entry in the contacts[] array on a client detail response."""

    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None
    name: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    secondaryEmail: Optional[str] = None
    mobile: Optional[str] = None
    phone: Optional[str] = None
    fax: Optional[str] = None
    notes: Optional[str] = None
    isActive: Optional[bool] = None
    isPrimary: Optional[bool] = None


class QuoteLite(BaseModel):
    """Slim quote record returned by GetQuotes?opportunityId=."""

    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None
    name: Optional[str] = None
    number: Optional[str] = None
    version: Optional[int] = None
    systemState: Optional[str] = None
    state: Optional[str] = None
    price: Optional[float] = None
    servicePrice: Optional[float] = None
    isIncludedInTotal: Optional[bool] = None
    isServiceQuote: Optional[bool] = None
    validUntilDate: Optional[datetime] = None
    acceptedDate: Optional[datetime] = None
    createdDate: Optional[datetime] = None
    modifiedDate: Optional[datetime] = None


class OpportunityDetail(BaseModel):
    """Full opportunity schema — GetOpportunity detail endpoint.

    Probe-confirmed: no `description` or `scopeOfWork` fields exist on the API
    response (keys absent, not null). Card-style rendering only.
    """

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    number: Optional[str] = None
    type: Optional[str] = None
    clientId: Optional[str] = None
    clientName: Optional[str] = None
    clientNumber: Optional[str] = None
    buildingType: Optional[str] = None
    marketSector: Optional[str] = None
    projectType: Optional[str] = None
    quoteType: Optional[str] = None
    quoteTemplate: Optional[str] = None
    systemState: Optional[str] = None
    stageGroup: Optional[str] = None
    stage: Optional[str] = None
    priority: Optional[str] = None
    price: Optional[float] = None
    servicePrice: Optional[float] = None
    budget: Optional[float] = None
    probability: Optional[int] = None
    owner: Optional[str] = None  # display name only — no ownerId on response
    projectArea: Optional[str] = None
    fulfillmentLocation: Optional[str] = None
    isExemptFromTax: Optional[bool] = None
    estimatedCloseDate: Optional[datetime] = None
    actualCloseDate: Optional[datetime] = None
    estimatedProjectStartDate: Optional[datetime] = None
    estimatedProjectEndDate: Optional[datetime] = None
    leadSource: Optional[str] = None
    lostReason: Optional[str] = None
    lostDescription: Optional[str] = None
    createdDate: Optional[datetime] = None
    modifiedDate: Optional[datetime] = None
    isArchived: Optional[bool] = None
    billingAddress: Optional[Address] = None
    siteAddress: Optional[Address] = None  # singular on Opp (vs siteAddresses[] on Client)
    contacts: Optional[list[Contact]] = None
    resources: Optional[list[dict]] = None  # pass-through, not modeled
    files: Optional[list[dict]] = None
    quoteIds: Optional[list[str]] = None


class OpportunityLite(BaseModel):
    """Slim opportunity schema for list responses (GetOpportunities).

    All fields confirmed present on list records per Phase 2 probe.
    Detail-only fields (quoteIds, contacts, siteAddress, billingAddress,
    fulfillmentLocation, lostReason, lostDescription, etc.) are NOT modeled here.
    """

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    number: Optional[str] = None
    type: Optional[str] = None
    clientId: Optional[str] = None
    clientName: Optional[str] = None
    clientNumber: Optional[str] = None
    systemState: Optional[str] = None
    stageGroup: Optional[str] = None
    stage: Optional[str] = None
    priority: Optional[str] = None
    price: Optional[float] = None
    servicePrice: Optional[float] = None
    probability: Optional[int] = None
    owner: Optional[str] = None
    buildingType: Optional[str] = None
    marketSector: Optional[str] = None
    projectType: Optional[str] = None
    createdDate: Optional[datetime] = None
    modifiedDate: Optional[datetime] = None
    isArchived: Optional[bool] = None


class ClientLite(BaseModel):
    """Minimal client schema for list responses."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    isActive: Optional[bool] = None
    modifiedDate: Optional[datetime] = None


class ClientDetail(ClientLite):
    """Full client schema — detail endpoint adds address/contact blocks.

    Phase 2 probe confirmed: no top-level `notes` field exists on clients
    (neither list nor detail). Use `markdown_card`, not `markdown_narrative`.
    """

    # Fields present on both list and detail
    type: Optional[str] = None
    number: Optional[str] = None
    email: Optional[str] = None
    mobile: Optional[str] = None
    phone: Optional[str] = None
    owner: Optional[str] = None
    hasSubaccounts: Optional[bool] = None
    createdDate: Optional[datetime] = None

    # Detail-only fields (absent from list response)
    billingAddress: Optional[Address] = None
    siteAddresses: Optional[list[Address]] = None
    contacts: Optional[list[Contact]] = None
    fax: Optional[str] = None
    secondaryEmail: Optional[str] = None
    website: Optional[str] = None
    isExemptFromTax: Optional[bool] = None
    files: Optional[list[dict]] = None
