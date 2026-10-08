# Image Integration Testing Playbook

## Test agent rules
- Always use base64-encoded images for image integration tests and requests.
- Accepted formats are JPEG, PNG, and WEBP only.
- Never use SVG, BMP, HEIC, blank, solid-color, or uniform-variance images.
- Every test image must contain real visual features such as text, objects, edges, textures, or shadows.
- Transcode unsupported formats to PNG or JPEG before upload, then re-detect and use the actual MIME type.
- For animated GIF, APNG, or WEBP, extract the first frame before testing.
- Resize large images to reasonable bounds and avoid oversized payloads.