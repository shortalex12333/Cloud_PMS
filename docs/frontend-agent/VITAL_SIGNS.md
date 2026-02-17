# Vital Signs Per Lens

> Facts from the database. Never summarize. Never editorialize. User decides what matters.
> Only show a count when zero/non-zero changes the operational meaning.

---

## Work Order
| Sign | Format |
|------|--------|
| Status | Pill: Pending / In Progress / Complete / Cancelled |
| Priority | Badge: Critical / High / Medium / Low |
| Parts | "X parts" — critical color if 0 and WO not complete |
| Age | "Created X days ago" or "Overdue by X days" |
| Equipment | Clickable link to Equipment lens |

## Equipment
| Sign | Format |
|------|--------|
| Status | Pill: Running / Fault / Offline |
| Last serviced | "X days ago" or "Never" |
| Open faults | "X open faults" — critical if > 0 |
| Certificate | "Valid" / "Expiring in X days" / "Expired" |
| Running hours | "X,XXX hrs" |

## Fault
| Sign | Format |
|------|--------|
| Severity | Pill |
| Status | Pill: Open / Assigned / In Progress / Resolved |
| Age | "Open X days" |
| Work order | Clickable link or "No work order" in warning |
| Equipment | Clickable link |

## Parts / Inventory
| Sign | Format |
|------|--------|
| Stock | "In stock (X)" / "Low" warning / "Critical" critical / "Zero" critical |
| Location | Text |
| Last consumed | "X days ago" or "Never" |
| Equipment | Clickable link |
| Unit cost | Formatted currency |

## Receiving
| Sign | Format |
|------|--------|
| Status | Pill: Expected / Arrived / Partial / Accepted / Rejected |
| Match rate | "X of Y verified" |
| Days since | "X days ago" or "Expected" |
| Shopping list | Clickable link or "No linked list" |
| Department | Text |

## Certificate
| Sign | Format |
|------|--------|
| Validity | Pill: Active / Expiring / Expired |
| Days remaining | "X days" or "Expired X days ago" |
| Type | Crew / Vessel |
| Issuing authority | Text |
| Linked entity | Clickable link |

## Handover
| Sign | Format |
|------|--------|
| Department | Text |
| Shift date | Formatted date |
| Status | Pill: Draft / Submitted / Acknowledged |
| Outstanding | "X outstanding" — warning if > 0 |
| Author | Name |

## Hours of Rest
| Sign | Format |
|------|--------|
| Crew member | Name |
| Period | Date range |
| Compliance | Pill: Compliant / Non-compliant / Incomplete |
| Total rest | "X hrs" |
| Status | Pill: Draft / Submitted / Approved |

## Warranty
| Sign | Format |
|------|--------|
| Status | Pill: Active / Expiring / Expired |
| Days remaining | "X days" or "Expired" |
| Equipment | Clickable link |
| Supplier | Text |

## Document
| Sign | Format |
|------|--------|
| Type | Badge |
| Version | "vX" |
| Updated | "X days ago" |
| Size | Formatted bytes |
| References | "Referenced by X entities" |

## Shopping List
| Sign | Format |
|------|--------|
| Status | Pill: Draft / Submitted / Ordered / Partially Received / Complete |
| Items | "X items" |
| Department | Text |
| Receivals | "X receivals" |
| Created | Date |
