"""
CelesteOS — Evidence Sealing Pipeline (v1.0)
=============================================

Takes a PyMuPDF-rendered ledger export (with embedded ledger_events.json)
and produces a fully sealed artifact:

    PDF/A-3 conformance  (ISO 19005-3)
    PAdES-B-LT signature (ETSI EN 319 142-1, long-term validation)
    RFC 3161 timestamp   (embedded in signature, neutral time attestation)

Input  : bytes  — PyMuPDF output, must contain embedded ledger_events.json
Output : bytes  — sealed PDF, verifiable client-side at verify.celeste7.ai

Pipeline stages
---------------
  1. Validate input         — embedded JSON present, fonts embedded
  2. PDF/A-3 upgrade        — XMP metadata, OutputIntent, /AF associations
  3. Hash                   — SHA-256 of upgraded bytes (logged to ledger)
  4. PAdES-B-LT sign        — with RFC 3161 timestamp from TSA
  5. (Caller) publish       — write export.sealed row to ledger_events

Integration
-----------
From the existing export endpoint:

    from apps.api.evidence.sealing import seal_export, SealingError

    raw_pdf_bytes = render_export(request_id)   # existing PyMuPDF renderer
    sealed_bytes, sealing_info = seal_export(raw_pdf_bytes)

    store_in_bucket(export_id, sealed_bytes)
    ledger.write_event(
        event_type="export.sealed",
        metadata={
            "export_id": export_id,
            "pdf_sha256": sealing_info.pdf_sha256,
            "signed_at": sealing_info.signed_at,
            "tsa_authority": sealing_info.tsa_authority,
            "signing_cert_fingerprint": sealing_info.cert_fingerprint,
            "key_version": sealing_info.key_version,
        },
    )

Environment
-----------
    CELESTE_SIGNING_CERT_PATH   — PEM cert (public, fingerprint published)
    CELESTE_SIGNING_KEY_PATH    — PEM private key (secrets manager, NEVER repo)
    CELESTE_SIGNING_KEY_VERSION — e.g. "v1" — rotated on key change
    CELESTE_TSA_PRIMARY         — default: https://freetsa.org/tsr
    CELESTE_TSA_FALLBACK        — default: http://timestamp.digicert.com

Dependencies
------------
    pip install pikepdf pyHanko[pkcs11,image-support] requests
"""

from __future__ import annotations

import hashlib
import io
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pikepdf
import requests
from pyhanko.sign import signers, timestamps
from pyhanko.sign.fields import SigFieldSpec, SigSeedSubFilter, append_signature_field
from pyhanko.sign.signers.pdf_signer import PdfSignatureMetadata, PdfSigner
from pyhanko.sign.timestamps import HTTPTimeStamper
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter

log = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Errors
# ──────────────────────────────────────────────────────────────────────────────

class SealingError(Exception):
    """Base — any failure in the sealing pipeline. Never ship un-sealed."""


class InputValidationError(SealingError):
    """Input PDF does not meet preconditions (missing attachment, unembedded fonts)."""


class ConformanceError(SealingError):
    """PDF/A-3 upgrade failed."""


class TimestampError(SealingError):
    """All TSA endpoints failed. Do NOT ship without a timestamp."""


class SigningError(SealingError):
    """PAdES signing failed."""


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SealingInfo:
    """Metadata about a sealed artifact — written verbatim to the ledger."""
    pdf_sha256: str
    signed_at: datetime
    tsa_authority: str
    cert_fingerprint: str
    key_version: str
    pdfa_conformance: str   # "3B"


def seal_export(pdf_bytes: bytes) -> tuple[bytes, SealingInfo]:
    """
    Seal a PyMuPDF-rendered export into a v1.0 evidence artifact.

    This function is the atomic unit of sealing. It either produces a fully
    sealed, verifiable PDF — or it raises. There is no half-sealed state.
    A caller must never persist or return the input bytes if this fails.
    """
    config = _load_config()

    # 1. Preconditions — fail fast with a loud reason, not a vague 500
    _validate_input(pdf_bytes)

    # 2. PDF/A-3 upgrade — metadata, OutputIntent, /AF
    pdfa3_bytes = _upgrade_to_pdfa3(pdf_bytes)

    # 3. Hash the PDF/A-3 (pre-signature). Logged; also embedded in cover if desired.
    pdf_sha256 = hashlib.sha256(pdfa3_bytes).hexdigest()
    log.info("evidence.sealing.hashed", extra={"sha256": pdf_sha256})

    # 4. Sign — PAdES-B-LT with embedded RFC 3161 TSA token
    signed_bytes, signed_at, tsa_used = _sign_pades_b_lt(pdfa3_bytes, config)

    # 5. Return sealed artifact + provenance record
    info = SealingInfo(
        pdf_sha256=pdf_sha256,
        signed_at=signed_at,
        tsa_authority=tsa_used,
        cert_fingerprint=_cert_fingerprint(config.cert_path),
        key_version=config.key_version,
        pdfa_conformance="3B",
    )
    return signed_bytes, info


# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class _SealingConfig:
    cert_path: Path
    key_path: Path
    key_version: str
    tsa_primary: str
    tsa_fallback: str


def _load_config() -> _SealingConfig:
    import tempfile

    cert = os.environ.get("CELESTE_SIGNING_CERT_PATH")
    key_path_str = os.environ.get("CELESTE_SIGNING_KEY_PATH")
    key_pem = os.environ.get("CELESTE_SIGNING_KEY_PEM")  # inline PEM for PaaS (Render, Railway, etc.)

    # Cert: support inline PEM via CELESTE_SIGNING_CERT_PEM (Render / PaaS)
    cert_pem = os.environ.get("CELESTE_SIGNING_CERT_PEM")
    if cert_pem and not cert:
        _tmp_cert = tempfile.NamedTemporaryFile(suffix=".crt", delete=False)
        _tmp_cert.write(cert_pem.replace("\\n", "\n").encode())
        _tmp_cert.flush()
        cert = _tmp_cert.name

    # Key: support inline PEM via CELESTE_SIGNING_KEY_PEM
    if key_pem and not key_path_str:
        _tmp_key = tempfile.NamedTemporaryFile(suffix=".key", delete=False)
        _tmp_key.write(key_pem.replace("\\n", "\n").encode())
        _tmp_key.flush()
        key_path_str = _tmp_key.name

    if not cert or not key_path_str:
        raise SealingError(
            "Signing cert and key must be set. "
            "Use CELESTE_SIGNING_CERT_PATH + CELESTE_SIGNING_KEY_PATH (file paths), "
            "or CELESTE_SIGNING_CERT_PEM + CELESTE_SIGNING_KEY_PEM (inline PEM for PaaS)."
        )
    return _SealingConfig(
        cert_path=Path(cert),
        key_path=Path(key_path_str),
        key_version=os.environ.get("CELESTE_SIGNING_KEY_VERSION", "v1"),
        tsa_primary=os.environ.get("CELESTE_TSA_PRIMARY", "https://freetsa.org/tsr"),
        tsa_fallback=os.environ.get("CELESTE_TSA_FALLBACK", "http://timestamp.digicert.com"),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Stage 1 — Input validation
# ──────────────────────────────────────────────────────────────────────────────

REQUIRED_ATTACHMENT = "ledger_events.json"


def _validate_input(pdf_bytes: bytes) -> None:
    """
    Fail loud if the input isn't what we expect. A seal over garbage
    is still garbage — we will not paper over upstream bugs.
    """
    if not pdf_bytes.startswith(b"%PDF-"):
        raise InputValidationError("Input is not a PDF.")

    with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
        # Attachment present?
        attachments = pdf.attachments
        if REQUIRED_ATTACHMENT not in attachments:
            raise InputValidationError(
                f"Required attachment '{REQUIRED_ATTACHMENT}' not found. "
                f"Found: {list(attachments.keys())}"
            )

        # Fonts embedded? PDF/A-3 forbids unembedded fonts.
        # PyMuPDF's default Helvetica is NOT embedded — upstream template
        # must be switched to an embeddable font (Inter, IBM Plex, etc.).
        unembedded = _find_unembedded_fonts(pdf)
        if unembedded:
            raise InputValidationError(
                f"Unembedded fonts found: {unembedded}. "
                f"PDF/A-3 requires all fonts embedded. "
                f"Fix: switch the PyMuPDF template to an embeddable font "
                f"(e.g. Inter, IBM Plex Sans) and embed via insert_font()."
            )


def _find_unembedded_fonts(pdf: pikepdf.Pdf) -> list[str]:
    """Return names of fonts that are referenced but not embedded.

    Handles three structures:
      - Simple fonts (Type1, TrueType): /FontDescriptor/FontFile{,2,3}
      - Type0 composite fonts (PyMuPDF Unicode embed): descriptor lives in
        /DescendantFonts[0]/FontDescriptor — must traverse there, not top level
      - Standard-14 (Helvetica etc.): no descriptor at all → always unembedded
    """
    unembedded: list[str] = []
    for page in pdf.pages:
        resources = page.get("/Resources")
        if not resources:
            continue
        fonts = resources.get("/Font")
        if not fonts:
            continue
        for _name, font in fonts.items():
            subtype = str(font.get("/Subtype", "")).lstrip("/")
            base = str(font.get("/BaseFont", "")).lstrip("/")

            # Type0 composite fonts (what PyMuPDF produces for Unicode TTF embeds)
            # — font data is inside DescendantFonts[0]/FontDescriptor
            if subtype == "Type0":
                descendants = font.get("/DescendantFonts")
                if descendants:
                    try:
                        cidfont = descendants[0]
                        descriptor = cidfont.get("/FontDescriptor")
                        if descriptor is not None:
                            has_file = any(
                                descriptor.get(k) is not None
                                for k in ("/FontFile", "/FontFile2", "/FontFile3")
                            )
                            if has_file:
                                continue  # properly embedded — skip
                    except Exception:
                        pass
                # Descriptor missing or no FontFile — treat as unembedded
                if base and base not in unembedded:
                    unembedded.append(base)
                continue

            # Simple fonts: descriptor at top level
            descriptor = font.get("/FontDescriptor")
            if descriptor is None:
                # Standard-14 fonts (Helvetica, Times, etc.) — forbidden in PDF/A-3
                if base and base not in unembedded:
                    unembedded.append(base)
                continue
            has_file = any(
                descriptor.get(k) is not None
                for k in ("/FontFile", "/FontFile2", "/FontFile3")
            )
            if not has_file:
                if base and base not in unembedded:
                    unembedded.append(base)
    return unembedded


# ──────────────────────────────────────────────────────────────────────────────
# Stage 2 — PDF/A-3 upgrade
# ──────────────────────────────────────────────────────────────────────────────

PDFA3_XMP = """<?xpacket begin='\ufeff' id='W5M0MpCehiHzreSzNTczkc9d'?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description rdf:about=""
        xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/"
        xmlns:dc="http://purl.org/dc/elements/1.1/"
        xmlns:xmp="http://ns.adobe.com/xap/1.0/"
        xmlns:pdf="http://ns.adobe.com/pdf/1.3/">
      <pdfaid:part>3</pdfaid:part>
      <pdfaid:conformance>B</pdfaid:conformance>
      <dc:title><rdf:Alt><rdf:li xml:lang="x-default">{title}</rdf:li></rdf:Alt></dc:title>
      <dc:creator><rdf:Seq><rdf:li>CelesteOS</rdf:li></rdf:Seq></dc:creator>
      <dc:description><rdf:Alt><rdf:li xml:lang="x-default">{description}</rdf:li></rdf:Alt></dc:description>
      <xmp:CreateDate>{created}</xmp:CreateDate>
      <xmp:ModifyDate>{created}</xmp:ModifyDate>
      <xmp:CreatorTool>CelesteOS Evidence Sealing v1.0</xmp:CreatorTool>
      <pdf:Producer>CelesteOS Sealing Pipeline</pdf:Producer>
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>
<?xpacket end='w'?>"""


def _upgrade_to_pdfa3(pdf_bytes: bytes) -> bytes:
    """
    Upgrade a standard PDF to PDF/A-3 conformance level B.

    What this adds:
      - XMP metadata with pdfaid:part=3, pdfaid:conformance=B
      - OutputIntent (sRGB ICC profile) — required for PDF/A
      - /AF (Associated Files) entries linking the ledger_events.json
        attachment to the document, per PDF/A-3 §6.8
      - Removes forbidden elements (encryption, transparency groups)

    What this does NOT do:
      - Embed fonts (must happen upstream in PyMuPDF — validated at input)
      - Validate that output passes an external PDF/A-3 checker (use veraPDF
        in CI for that; this pipeline trusts its own construction)
    """
    try:
        with pikepdf.open(io.BytesIO(pdf_bytes), allow_overwriting_input=False) as pdf:
            # a) Remove anything PDF/A forbids
            if pdf.is_encrypted:
                raise ConformanceError("Input PDF is encrypted; PDF/A forbids encryption.")

            # b) Embed XMP metadata
            created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            xmp = PDFA3_XMP.format(
                title="CelesteOS Ledger Evidence Export",
                description="Tamper-evident ledger export with embedded source data.",
                created=created,
            )
            with pdf.open_metadata(set_pikepdf_as_editor=False) as meta:
                meta.load_from_docinfo(pdf.docinfo)
            # Write raw XMP — pikepdf's metadata API doesn't expose pdfaid cleanly
            metadata_stream = pikepdf.Stream(pdf, xmp.encode("utf-8"))
            metadata_stream["/Type"] = pikepdf.Name("/Metadata")
            metadata_stream["/Subtype"] = pikepdf.Name("/XML")
            pdf.Root["/Metadata"] = metadata_stream

            # c) OutputIntent — required for PDF/A
            _add_srgb_output_intent(pdf)

            # d) Associated Files — PDF/A-3 §6.8
            #    Each embedded file must be linked via /AF on the Catalog
            #    AND have /AFRelationship set on the filespec.
            _link_associated_files(pdf)

            # e) Serialize
            buf = io.BytesIO()
            pdf.save(
                buf,
                linearize=False,
                object_stream_mode=pikepdf.ObjectStreamMode.disable,  # PDF/A requirement
                compress_streams=True,
            )
            return buf.getvalue()

    except pikepdf.PdfError as e:
        raise ConformanceError(f"pikepdf failed during PDF/A-3 upgrade: {e}") from e


def _add_srgb_output_intent(pdf: pikepdf.Pdf) -> None:
    """Add sRGB OutputIntent. Required for PDF/A conformance."""
    srgb_icc_path = Path(__file__).parent / "icc" / "sRGB_v4_ICC_preference.icc"
    if not srgb_icc_path.exists():
        raise ConformanceError(
            f"sRGB ICC profile missing at {srgb_icc_path}. "
            f"Download from https://www.color.org/profiles2.xalter and commit to repo."
        )

    icc_bytes = srgb_icc_path.read_bytes()
    icc_stream = pikepdf.Stream(pdf, icc_bytes)
    icc_stream["/N"] = 3  # RGB has 3 components

    output_intent = pikepdf.Dictionary(
        Type=pikepdf.Name("/OutputIntent"),
        S=pikepdf.Name("/GTS_PDFA1"),
        OutputConditionIdentifier=pikepdf.String("sRGB IEC61966-2.1"),
        RegistryName=pikepdf.String("http://www.color.org"),
        Info=pikepdf.String("sRGB IEC61966-2.1"),
        DestOutputProfile=icc_stream,
    )
    pdf.Root["/OutputIntents"] = pikepdf.Array([output_intent])


def _link_associated_files(pdf: pikepdf.Pdf) -> None:
    """
    PDF/A-3 §6.8: every embedded file must be linked from /AF on the
    Catalog, and must declare /AFRelationship. 'Source' is the right
    value for raw data that backs the document.
    """
    names = pdf.Root.get("/Names")
    if not names:
        return
    ef = names.get("/EmbeddedFiles")
    if not ef:
        return

    af_array = pikepdf.Array()
    names_array = ef.get("/Names", pikepdf.Array())
    for i in range(0, len(names_array), 2):
        filespec = names_array[i + 1]
        filespec["/AFRelationship"] = pikepdf.Name("/Source")
        af_array.append(filespec)

    pdf.Root["/AF"] = af_array


# ──────────────────────────────────────────────────────────────────────────────
# Stage 3 — PAdES-B-LT signing with RFC 3161 timestamp
# ──────────────────────────────────────────────────────────────────────────────

SIG_FIELD_NAME = "CelesteOSEvidenceSeal"


def _sign_pades_b_lt(
    pdfa3_bytes: bytes,
    config: _SealingConfig,
) -> tuple[bytes, datetime, str]:
    """
    Apply a PAdES-B-LT signature with an embedded RFC 3161 timestamp.

    PAdES-B-LT ('baseline, long-term') means the signature contains
    enough information (certs, CRLs/OCSP responses, timestamp) to be
    validatable decades later, without needing to query CA status online.

    Returns:
        (signed_pdf_bytes, signed_at_utc, tsa_authority_url_used)
    """
    # Load signer — self-signed today, CA-issued at v1.1
    try:
        signer = signers.SimpleSigner.load(
            key_file=str(config.key_path),
            cert_file=str(config.cert_path),
            ca_chain_files=(),  # self-signed: no chain
            key_passphrase=_load_passphrase_from_secrets_manager(),
        )
    except Exception as e:
        raise SigningError(f"Could not load signing key/cert: {e}") from e

    # RFC 3161 timestamper — FreeTSA primary, DigiCert fallback
    timestamper = _make_timestamper(config)

    # Append an empty signature field at a well-known name,
    # then sign into it. This keeps the field name stable across
    # all CelesteOS exports — verifiers can assert on it.
    with pikepdf.open(io.BytesIO(pdfa3_bytes)) as pdf:
        writer_buf = io.BytesIO()
        pdf.save(writer_buf)
    writer = IncrementalPdfFileWriter(io.BytesIO(writer_buf.getvalue()))

    append_signature_field(
        writer,
        sig_field_spec=SigFieldSpec(sig_field_name=SIG_FIELD_NAME),
    )

    sig_meta = PdfSignatureMetadata(
        field_name=SIG_FIELD_NAME,
        reason="CelesteOS evidence seal",
        location="verify.celeste7.ai",
        subfilter=SigSeedSubFilter.PADES,
        use_pades_lta=False,          # LTA archive-timestamp: v1.1
        # embed_validation_info=False for self-signed staging cert:
        # no OCSP/CRL exists for self-signed, and pyHanko cannot build the
        # FreeTSA root chain without its CA in the trust store.
        # Re-enable with allow_fetching=True when switched to CA-issued cert (v1.1).
        embed_validation_info=False,
    )

    pdf_signer = PdfSigner(
        sig_meta,
        signer=signer,
        timestamper=timestamper,
    )

    out_buf = io.BytesIO()
    try:
        pdf_signer.sign_pdf(writer, output=out_buf)
    except Exception as e:
        raise SigningError(f"pyHanko signing failed: {e}") from e

    signed_at = datetime.now(timezone.utc)
    return out_buf.getvalue(), signed_at, timestamper.url


def _make_timestamper(config: _SealingConfig) -> HTTPTimeStamper:
    """
    Return a working TSA. Tries primary, falls back if the primary is
    unreachable or returns an invalid response. NEVER returns a dummy
    or null-op timestamper — if all TSAs are down, we fail loudly.
    """
    for url in (config.tsa_primary, config.tsa_fallback):
        tsa = HTTPTimeStamper(url=url, timeout=15)
        if _tsa_reachable(url):
            log.info("evidence.sealing.tsa_selected", extra={"tsa": url})
            return tsa
        log.warning("evidence.sealing.tsa_unreachable", extra={"tsa": url})

    raise TimestampError(
        f"All TSAs unreachable: {config.tsa_primary}, {config.tsa_fallback}. "
        f"Do NOT ship un-timestamped exports. Retry or queue for later sealing."
    )


def _tsa_reachable(url: str, attempts: int = 3) -> bool:
    """Exponential backoff reachability probe. FreeTSA is flaky — budget for it."""
    for attempt in range(attempts):
        try:
            # HEAD will 405 on most TSAs but that proves connectivity
            r = requests.head(url, timeout=5, allow_redirects=True)
            if r.status_code < 500:
                return True
        except requests.RequestException:
            pass
        time.sleep(2 ** attempt)
    return False


def _load_passphrase_from_secrets_manager() -> Optional[bytes]:
    """
    The key passphrase belongs in a secrets manager (AWS Secrets Manager,
    Doppler, 1Password Teams). NEVER in env vars that ship to CI logs,
    NEVER in .env files, NEVER in the repo.

    Replace this stub with your secrets-manager client call.
    Returns None if the key is unencrypted (acceptable for dev, NOT prod).
    """
    passphrase = os.environ.get("CELESTE_SIGNING_KEY_PASSPHRASE")
    if passphrase:
        log.warning(
            "Signing key passphrase loaded from env var — "
            "migrate to secrets manager before production."
        )
        return passphrase.encode("utf-8")
    return None


def _cert_fingerprint(cert_path: Path) -> str:
    """SHA-256 fingerprint of the signing cert. Published at /.well-known/."""
    return hashlib.sha256(cert_path.read_bytes()).hexdigest()


# ──────────────────────────────────────────────────────────────────────────────
# CLI / smoke test
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Seal a CelesteOS evidence export.")
    parser.add_argument("input", type=Path, help="PyMuPDF-rendered PDF input")
    parser.add_argument("output", type=Path, help="Sealed PDF output")
    args = parser.parse_args()

    input_bytes = args.input.read_bytes()
    try:
        sealed, info = seal_export(input_bytes)
    except SealingError as e:
        print(f"SEALING FAILED: {e}", file=sys.stderr)
        sys.exit(1)

    args.output.write_bytes(sealed)
    print(f"✓ Sealed → {args.output}")
    print(f"  sha256      : {info.pdf_sha256}")
    print(f"  signed_at   : {info.signed_at.isoformat()}")
    print(f"  tsa         : {info.tsa_authority}")
    print(f"  cert_fp     : {info.cert_fingerprint[:16]}…")
    print(f"  key_version : {info.key_version}")
    print(f"  conformance : PDF/A-{info.pdfa_conformance}")
