## Directory: development/trusted_certs

Place all trusted certificates as `.crt` files in this directory.

### About `*.crt` Files

`*.crt` files are used to store SSL/TLS certificates. These files are typically encoded in PEM (Privacy-Enhanced Mail) format, which is a base64 encoded format with header and footer lines. The header and footer lines look like this:

```
-----BEGIN CERTIFICATE-----
[Base64 encoded certificate]
-----END CERTIFICATE-----
```

Ensure that your `.crt` files follow this format before placing them in the directory.
