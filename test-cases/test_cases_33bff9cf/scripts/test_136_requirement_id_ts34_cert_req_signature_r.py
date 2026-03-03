```python
# File: tests/test_certificate_signature_strength.py

"""
Test Case for:
Requirement ID : TS.34_CERT_REQ_SIGNATURE

Requirement:
Certificates SHOULD abide by contemporary standards for signature strength.
- RSA minimum 2048 bits, ECDSA/ECC minimum 224 bits, SHA-256 or stronger.

References:
- GSMA TS.34 v8.0, TS.34_CERT_REQ_SIGNATURE, Section 5.10
- SGP.02 v4.2 Section 2.3.3 and Appendix A.10
- RFC 5280, RFC 7512, RFC 7525, NIST SP 800-57
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
- 0030535f-1fd5-4ecc-963d-67ed8cff3f98_SGP.02-v4.2.pdf
"""

import pytest
import subprocess
import os
import re

# ---- CONFIGURATION ----
# File path(s) to PEM certificates to be tested (replace or parametrize for automation)
CERT_FILES = [
    "certs/server-cert.pem",
    "certs/client-cert.pem",
    "certs/ca-cert.pem",
    # Add paths or parametrize as needed
]

# Signature algorithm and key strength requirements
ALLOWED_SIGNATURE_ALGOS = {
    "sha256WithRSAEncryption",
    "sha384WithRSAEncryption",
    "sha512WithRSAEncryption",
    "ecdsa-with-SHA256",
    "ecdsa-with-SHA384",
    "ecdsa-with-SHA512"
}
MIN_RSA_BITS = 2048
MIN_ECC_BITS = 224

# Utility: parse OpenSSL key size output string (modulus length for RSA, key size for EC)
def parse_keysize_from_openssl_output(text):
    # Look for e.g. "RSA Public-Key: (2048 bit)", "Public-Key: (256 bit)"
    m = re.search(r": \((\d+)\s*bit\)", text)
    if m:
        return int(m.group(1))
    return None

def get_certificate_details(cert_path):
    """
    Extracts details (signature algorithm, key size, ...) from certificate using OpenSSL.
    """
    if not os.path.isfile(cert_path):
        raise FileNotFoundError(f"Certificate file not found: {cert_path}")

    # Read the cert and parse signature algorithm
    try:
        # Get signature algorithm (from text)
        result = subprocess.run(
            ["openssl", "x509", "-in", cert_path, "-text", "-noout"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True
        )
        txt = result.stdout

        # Parse signature algorithm
        sig_alg_match = re.search(r"Signature Algorithm: ([^\n]+)", txt)
        sig_algo = sig_alg_match.group(1).strip() if sig_alg_match else None

        # Parse key type (RSA, EC, ...)
        pubkey_match = re.search(r"Public Key Algorithm: ([^\n]+)", txt)
        key_type = pubkey_match.group(1).strip() if pubkey_match else None

        # Get key size
        key_size = None
        if "rsa" in (key_type or "").lower():
            # Use "openssl rsa" on public key file
            pkout = subprocess.run(
                ["openssl", "x509", "-in", cert_path, "-pubkey", "-noout"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True
            )
            pubkey = pkout.stdout
            # Write the pubkey to temp and parse size
            with open("temp_pubkey.pem", "w") as f:
                f.write(pubkey)
            pkparse = subprocess.run(
                ["openssl", "rsa", "-pubin", "-in", "temp_pubkey.pem", "-text", "-noout"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            key_size = parse_keysize_from_openssl_output(pkparse.stdout)
            try:
                os.remove("temp_pubkey.pem")
            except Exception:
                pass
        elif "ec" in (key_type or "").lower():
            pkout = subprocess.run(
                ["openssl", "x509", "-in", cert_path, "-pubkey", "-noout"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True
            )
            pubkey = pkout.stdout
            with open("temp_ecpub.pem", "w") as f:
                f.write(pubkey)
            pkparse = subprocess.run(
                ["openssl", "ec", "-pubin", "-in", "temp_ecpub.pem", "-text", "-noout"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            key_size = parse_keysize_from_openssl_output(pkparse.stdout)
            try:
                os.remove("temp_ecpub.pem")
            except Exception:
                pass
        else:
            key_size = None
        return {
            "signature_algorithm": sig_algo,
            "key_type": key_type,
            "key_size": key_size
        }
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error invoking OpenSSL: {e.stderr or str(e)}")

# ---- TEST ----

@pytest.mark.parametrize("cert_path", CERT_FILES)
def test_certificate_signature_strength(cert_path):
    """
    TS.34_CERT_REQ_SIGNATURE:
      - Certificates must use strong, contemporary signature and key algorithms.
      - Check for RSA >= 2048, ECC >= 224, SHA-256+ for signatures.
    """
    details = get_certificate_details(cert_path)
    sig_algo = details["signature_algorithm"]
    key_type = details["key_type"]
    key_size = details["key_size"]

    print(f"Testing certificate: {cert_path}")
    print(f"Signature Algorithm: {sig_algo}, Key Type: {key_type}, Key Size: {key_size}")

    # a) Signature algorithm should be allowed/modern (match RFC 5280/TS.34/SGP.02 requirements)
    assert sig_algo in ALLOWED_SIGNATURE_ALGOS, (
        f"Non-contemporary signature algorithm: {sig_algo} for cert {cert_path}"
    )

    # b) Key type and size: check for minimum bits
    if "rsa" in (key_type or "").lower():
        assert key_size is not None and key_size >= MIN_RSA_BITS, (
            f"RSA key too short for {cert_path} (found: {key_size} bits, required: {MIN_RSA_BITS} bits)"
        )
    elif "ec" in (key_type or "").lower():
        assert key_size is not None and key_size >= MIN_ECC_BITS, (
            f"ECC key too short for {cert_path} (found: {key_size} bits, required: {MIN_ECC_BITS} bits)"
        )
    else:
        assert False, f"Unknown or unsupported key type: {key_type}"

    # (Optional) Step 6: Could integrate with an external scanner/analysis tool here

    print(f"Certificate {cert_path} passes signature strength checks (algorithm/key size OK).")

def test_no_weak_signature_algorithms_in_all_certificates():
    """
    TS.34_CERT_REQ_SIGNATURE:
      - No certificate may use deprecated or weak signature algorithms (SHA-1, MD5, RSA<2048, ECC<224).
    """
    deprecated_algos = {"sha1WithRSAEncryption", "md5WithRSAEncryption", "md2WithRSAEncryption"}
    for cert_path in CERT_FILES:
        details = get_certificate_details(cert_path)
        sig_algo = details["signature_algorithm"]
        key_type = details["key_type"]
        key_size = details["key_size"]
        assert sig_algo not in deprecated_algos, (
            f"Weak/deprecated signature algorithm found in {cert_path}: {sig_algo}"
        )
        if "rsa" in (key_type or "").lower():
            assert key_size is not None and key_size >= MIN_RSA_BITS, (
                f"Weak RSA key in {cert_path} (found: {key_size} bits, required: {MIN_RSA_BITS} bits)"
            )
        if "ec" in (key_type or "").lower():
            assert key_size is not None and key_size >= MIN_ECC_BITS, (
                f"Weak ECC key in {cert_path} (found: {key_size} bits, required: {MIN_ECC_BITS} bits)"
            )
    print(f"All checked certificates use only strong, contemporary signature algorithms and keys.")
```

---

**How to use/adapt:**
- Save this script as `tests/test_certificate_signature_strength.py`.
- Replace `CERT_FILES` with the actual list of PEM certificate files you want to test.
- Ensure `openssl` command-line tool is available on your test machine.
- Run with:
  ```bash
  pytest tests/test_certificate_signature_strength.py
  ```
- All checks and logs are mapped to GSMA TS.34_CERT_REQ_SIGNATURE and referenced industry/NIST/SGP.02 standards.
- For automation, extend or parametrize for scanning a directory of certificates, or integrate with CI pipelines/certificate monitoring tools.
- The test covers both signature algorithm and key size/strength criteria and blocks/flags any weak or outdated configuration.

Let me know if you need integration with remote APIs, scanners, or live certificate repositories!